"""One hosted H operator per run; the controller keeps tools, budget and records local."""
from importlib.resources import files
import json
import multiprocessing
from pathlib import Path
import queue
import threading
import time

from jesse.research import BUDGET_SECONDS, MAX_STEPS, SEARCH_URL, Note, brief
from jesse.personality import character
from jesse.runtime import conversation_event, json_value, save_json, stop_worker
from .lab import Lab
from .tools import agent_tools

MODEL = "holo4-27b"
# H can freeze mid-run (seen: no event for 100 min, then an internal error). While H is meant to be working,
# this much silence ends the run instead of waiting out the whole budget.
STALL_SECONDS = 60


class AgentStalled(Exception):
    pass


def _pump(stream, events: "queue.Queue[tuple[str, object]]") -> None:
    """Read H events on a side thread so the controller can notice when they stop coming."""
    try:
        for event in stream:
            events.put(("event", event))
        events.put(("end", None))
    except BaseException as error:  # Forwarded to the controller thread, which decides.
        events.put(("error", error))


def watch(stream, stall_seconds: float):
    """Yield H events; raise AgentStalled after `stall_seconds` without one while H is working (not idle)."""
    events: queue.Queue[tuple[str, object]] = queue.Queue()
    threading.Thread(target=_pump, args=(stream, events), name="h-events", daemon=True).start()
    last, idle = time.monotonic(), False
    while True:
        try:
            kind, item = events.get(timeout=min(5.0, stall_seconds / 2))
        except queue.Empty:
            if not idle and time.monotonic() - last > stall_seconds:
                raise AgentStalled(f"No H event for {stall_seconds:g} s") from None
            continue
        if kind == "end":
            return
        if kind == "error":
            raise item
        last = time.monotonic()
        payload = json_value(item)
        if payload.get("type") == "ActiveStateChangeEvent":
            idle = (payload.get("data") or {}).get("state") == "idle"
        yield payload


SURFACES = ("web", "desktop")


def environment(surface: str) -> dict:
    if surface == "web":
        return {"id": "jesse-browser", "kind": "web", "start_url": SEARCH_URL,
                "mode": {"type": "visual", "width": 1280, "height": 900}}
    return {"id": "jesse-desktop", "kind": "desktop", "host": "user_device", "shell": False}


def build_prompt(notes: tuple[Note, ...], surface: str, question: str) -> str:
    where = (f"You work in a hosted browser that starts on a search engine ({SEARCH_URL})." if surface == "web" else
             "You work on the researcher's own desktop through the local bridge; open their applications there.")
    return "\n\n".join((
        "Researcher question: " + json.dumps(question),
        where,
        character(),
        files("jesse").joinpath("instructions.md").read_text(encoding="utf-8"),
        "# The researcher's notes (background and usual tools)\n\n" + brief(notes),
    ))


def execute(folder: Path, surface: str, budget_seconds: int,
            question: str = "", interactive: bool = False, client=None, stall_seconds: float = STALL_SECONDS) -> None:
    from hai_agents import Client

    lab = Lab(folder, question)
    started = time.monotonic()
    handle = None
    try:
        handle = (client or Client(timeout=30)).start_session(
            agent={"name": "jesse", "description": "Lab assistant", "model": MODEL, "reasoning_effort": "low",
                   "environments": [environment(surface)]},
            messages=(folder / "protocol.md").read_text(encoding="utf-8"),
            tools=agent_tools(lab), max_time_s=budget_seconds, max_steps=MAX_STEPS,
            **({"idle_timeout_s": 90} if interactive else {}))
        save_json(folder, "session.json", {"id": handle.id, "agent_view_url": None})
        metadata = handle.get()
        save_json(folder, "session.json", {"id": handle.id, "agent_view_url": metadata.agent_view_url})
        print(f"Agent View: {metadata.agent_view_url}", flush=True)
        conversation_event(folder, "session", "Laboratory opening.", speak=True)
        stream = handle.stream(timeout_seconds=max(1, budget_seconds - (time.monotonic() - started)), wait_for_seconds=5,
                               until="terminal" if interactive else "settled")
        for payload in watch(stream, stall_seconds):
            with (folder / "events.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(payload, allow_nan=False) + "\n")
            data = payload.get("data") or {}
            if data.get("kind") == "answer_event":
                (folder / "agent-report.md").write_text(str(data.get("answer", "")), encoding="utf-8")
                lab.finish("The agent answered; measurements and verification require replay review.")
                if interactive:
                    conversation_event(folder, "report_ready", "My current report is ready. You can ask a follow-up while this session remains open.")
            if payload.get("type") == "ActiveStateChangeEvent":
                save_json(folder, "session-state.json", {"state": data.get("state")})
        result = handle.wait_for_completion(timeout_seconds=5)
        save_json(folder, "session.json", {**json_value(result), "id": handle.id, "agent_view_url": metadata.agent_view_url})
        (folder / "agent-report.md").write_text(str(result.answer or "No final agent answer."), encoding="utf-8")
        lab.finish("Session finished. Review measurements, repeats and the replay before accepting a conclusion.")
    except AgentStalled as error:
        save_json(folder, "stall.json", {"reason": str(error), "stall_seconds": stall_seconds})
        conversation_event(folder, "blocker", "The lab agent stopped responding. I closed the session and kept the measurements.", speak=True)
        lab.finish(f"H stopped responding ({error}); the session was closed and earlier evidence is retained.")
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


def run_investigation(folder: Path, notes: tuple[Note, ...], surface: str, budget_seconds: int,
                      question: str, interactive: bool = False) -> int:
    if surface not in SURFACES:
        raise ValueError(f"Unknown surface {surface}; use web or desktop")
    if not 1 <= budget_seconds <= BUDGET_SECONDS:
        raise ValueError(f"Execution budget must be between 1 and {BUDGET_SECONDS} seconds")
    lab = Lab(folder, question)
    (folder / "protocol.md").write_text(build_prompt(notes, surface, question), encoding="utf-8")
    worker = multiprocessing.get_context("spawn").Process(
        target=execute, args=(folder, surface, budget_seconds, question, interactive))
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
