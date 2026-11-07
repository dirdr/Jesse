"""One hosted H operator per run; the controller keeps tools, budget and records local."""
from importlib.resources import files
import json
import multiprocessing
from pathlib import Path
import time

from jesse.contexts import ResearchContext, load_extension
from jesse.personality import character
from jesse.runtime import conversation_event, json_value, save_json, stop_worker
from .lab import Lab
from .tools import builtin_tools

MODEL = "holo4-27b"


def build_prompt(context: ResearchContext, surface: str, question: str) -> str:
    target = context.surfaces[surface]
    where = (f"Execution surface: hosted visual browser, starting at {target.start_url}." if surface == "web" else
             "Execution surface: the researcher's local desktop through the local bridge."
             + (f" The application is installed at {target.app_path}." if target.app_path else ""))
    return "\n\n".join((
        "Researcher question (context; execute the bounded protocol): " + json.dumps(question),
        where,
        character(),
        files("jesse").joinpath("instructions.md").read_text(encoding="utf-8"),
        context.protocol,
    ))


def context_tools(lab: Lab) -> list:
    tools = builtin_tools(lab, lab.context.tools)
    factory = getattr(lab.extension, "tools", None)
    if callable(factory):
        tools += list(factory(lab))
    names = [tool.__name__ for tool in tools]
    if len(names) != len(set(names)):
        raise ValueError(f"Duplicate tool names in context {lab.context.id}: {names}")
    return tools


def execute(folder: Path, context: ResearchContext, surface: str, budget_seconds: int,
            question: str = "", interactive: bool = False, client=None) -> None:
    from hai_agents import Client

    lab = Lab(folder, context, question, load_extension(context))
    started = time.monotonic()
    handle = None
    try:
        handle = (client or Client(timeout=30)).start_session(
            agent={"name": f"jesse-{context.id}", "description": context.title, "model": MODEL, "reasoning_effort": "low",
                   "environments": [context.surfaces[surface].environment(context.id)]},
            messages=(folder / "protocol.md").read_text(encoding="utf-8"),
            tools=context_tools(lab), max_time_s=budget_seconds, max_steps=context.max_steps,
            **({"idle_timeout_s": 90} if interactive else {}))
        save_json(folder, "session.json", {"id": handle.id, "agent_view_url": None})
        metadata = handle.get()
        save_json(folder, "session.json", {"id": handle.id, "agent_view_url": metadata.agent_view_url})
        print(f"Agent View: {metadata.agent_view_url}", flush=True)
        conversation_event(folder, "session", "Laboratory opening.", speak=True)
        for event in handle.stream(timeout_seconds=max(1, budget_seconds - (time.monotonic() - started)), wait_for_seconds=5,
                                   until="terminal" if interactive else "settled"):
            payload = json_value(event)
            with (folder / "events.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(payload, allow_nan=False) + "\n")
            data = payload.get("data") or {}
            if data.get("kind") == "answer_event":
                (folder / "agent-report.md").write_text(str(data.get("answer", "")), encoding="utf-8")
                lab.finish("The agent answered; measurements and verification require replay review.")
                if interactive:
                    conversation_event(folder, "waiting", "My current report is ready. You can ask a follow-up while this session remains open.")
            if payload.get("type") == "ActiveStateChangeEvent":
                save_json(folder, "session-state.json", {"state": data.get("state")})
        result = handle.wait_for_completion(timeout_seconds=5)
        save_json(folder, "session.json", {**json_value(result), "id": handle.id, "agent_view_url": metadata.agent_view_url})
        (folder / "agent-report.md").write_text(str(result.answer or "No final agent answer."), encoding="utf-8")
        lab.finish("Session finished. Review measurements, repeats and the replay before accepting a conclusion.")
    except (KeyboardInterrupt, TimeoutError) as error:
        lab.finish("The run was stopped or reached its time budget; earlier evidence is retained.")
        if isinstance(error, KeyboardInterrupt):
            raise
    except Exception as error:
        save_json(folder, "error.json", {"type": type(error).__name__, "message": str(error)[:500]})
        lab.finish(f"Execution stopped ({type(error).__name__}); prior evidence is retained.")
    finally:
        if handle is not None:
            try:
                handle.cancel()
            except Exception as error:
                save_json(folder, "cleanup.json", {"cancellation": "failed", "error_type": type(error).__name__})
        outcome = json.loads((folder / "outcome.json").read_text()).get("outcome", "inconclusive") if (folder / "outcome.json").exists() else "inconclusive"
        conversation_event(folder, "finished", f"Done. Outcome: {outcome.replace('_', ' ')}. The report is ready.", speak=True)


def run_investigation(folder: Path, context: ResearchContext, surface: str, budget_seconds: int,
                      question: str, interactive: bool = False) -> int:
    if surface not in context.surfaces:
        raise ValueError(f"Context {context.id} does not declare the {surface} surface")
    if not 1 <= budget_seconds <= 600:
        raise ValueError("Execution budget must be between 1 and 600 seconds")
    lab = Lab(folder, context, question)
    (folder / "protocol.md").write_text(build_prompt(context, surface, question), encoding="utf-8")
    worker = multiprocessing.get_context("spawn").Process(
        target=execute, args=(folder, context, surface, budget_seconds, question, interactive))
    try:
        worker.start()
        worker.join(budget_seconds)
        if worker.is_alive():
            stop_worker(worker)
            lab.finish("Run budget exhausted; operator stopped and earlier evidence retained.")
            return 1
    except KeyboardInterrupt:
        stop_worker(worker)
        lab.finish("Stopped by the researcher; earlier evidence retained.")
        return 130
    outcome = json.loads((folder / "outcome.json").read_text()) if (folder / "outcome.json").exists() else None
    if outcome is None:
        lab.finish("Worker exited unexpectedly; inspect saved events.")
        return 1
    return 1 if outcome["outcome"] == "blocked" else 0
