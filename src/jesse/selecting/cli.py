"""Research question → research context → bounded computer-use experiment."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from jesse.contexts import ContextError, ResearchContext, load_contexts
from jesse.investigating.runner import MODEL, run_investigation
from jesse.preflight import check_surface, checks_payload
from jesse.runtime import conversation_event
from jesse.personality import get_persona
from .adapters import HExperimentPlanner, PydanticExperimentPlanner
from .application import select_experiment
from .domain import PlannerUnavailable, Selection


def save_json(folder: Path, name: str, payload: dict | list) -> None:
    path = folder / name
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False, default=str), encoding="utf-8")
    temporary.replace(path)


def save_selection_report(folder: Path, selection: Selection, plan_only: bool) -> None:
    reason = selection.reason
    outcome = "blocked" if selection.status == "blocked" else "inconclusive"
    if plan_only and selection.status == "ready":
        reason += " Plan-only mode: no simulator was operated."
    save_json(folder, "outcome.json", {
        "run_id": folder.name, "outcome": outcome, "reason": reason,
        "verification": "not_started", "finished_at": datetime.now(timezone.utc).isoformat(),
    })
    (folder / "report.md").write_text(
        "# Investigation selection\n\n" + f"Outcome: **{outcome}**\n\n{reason}\n\n"
        + "[Research question](request.json) · [Catalogue](catalogue.json) · "
        + "[Availability](availability.json) · [Selection](selection.json)\n\n"
        + "No measurements were taken during selection.\n", encoding="utf-8",
    )


def pinned_selection(question: str, context: ResearchContext, available: set[str], requested: str) -> Selection:
    question = question.strip()
    if not question or len(question) > 4000:
        return Selection("blocked", question, "Supply a research question between 1 and 4000 characters.")
    candidates = [requested] if requested != "auto" else sorted(context.surfaces, key=lambda name: name != "web")
    surface = next((name for name in candidates if name in context.surfaces and name in available), None)
    if surface is None:
        return Selection("blocked", question, f"{context.title} has no available surface. Inspect availability.json for setup requirements.")
    return Selection("ready", question, f"Research context chosen at launch: {context.title}.", context.id, surface, context.max_trials)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", help="Research question to match against the research contexts")
    parser.add_argument("--catalogue", action="store_true", help="List research contexts without calling an API")
    parser.add_argument("--contexts", type=Path, help="Folder of research contexts (default: ./contexts or JESSE_CONTEXTS_DIR)")
    parser.add_argument("--context", help="Use this research context directly, without the selector")
    parser.add_argument("--surface", choices=("auto", "web", "desktop"), default="auto")
    parser.add_argument("--planner", choices=("openai", "h"), default="openai")
    parser.add_argument("--planner-model", help="Provider model; defaults to OPENAI_MODEL/gpt-5-mini or holo4-27b")
    parser.add_argument("--plan-only", action="store_true", help="Select a context without operating scientific software")
    parser.add_argument("--timeout", type=int, default=600, metavar="SECONDS", help="Shared selection and execution budget, 1–600 seconds")
    parser.add_argument("--interactive", action="store_true", help="Keep the session open for bounded conversation")
    parser.add_argument("--run-dir", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        catalogue = load_contexts(args.contexts)
    except ContextError as error:
        parser.error(str(error))
    if args.catalogue:
        print(json.dumps([item.to_dict() for item in catalogue], indent=2, ensure_ascii=False))
        return 0
    if args.question is None:
        parser.error("Supply a research question or use --catalogue")
    if not 1 <= args.timeout <= 600:
        parser.error("--timeout must be between 1 and 600 seconds")
    pinned = next((item for item in catalogue if item.id == args.context), None)
    if args.context and pinned is None:
        parser.error(f"Unknown research context {args.context!r}; run jesse --catalogue")

    started = time.monotonic()
    folder = args.run_dir or Path("runs") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    if args.run_dir is not None and (folder / "request.json").exists():
        parser.error("The supplied run directory already contains an investigation")
    folder.mkdir(parents=True, exist_ok=args.run_dir is not None)
    if not (folder / "persona.json").exists():
        save_json(folder, "persona.json", {"id": get_persona().id})
    print(f"Artifacts: {folder}", flush=True)
    model = args.planner_model or (os.environ.get("OPENAI_MODEL", "gpt-5-mini") if args.planner == "openai" else MODEL)
    request = {"run_id": folder.name, "question": args.question, "surface_preference": args.surface,
               "context": args.context, "planner": None if pinned else args.planner,
               "planner_model": None if pinned else model, "budget_seconds": args.timeout,
               "started_at": datetime.now(timezone.utc).isoformat()}
    save_json(folder, "request.json", request)
    save_json(folder, "catalogue.json", [item.to_dict() for item in catalogue])
    surfaces = sorted({name for item in ((pinned,) if pinned else catalogue) for name in item.surfaces})
    availability = {surface: checks_payload(check_surface(surface)) for surface in surfaces}
    save_json(folder, "availability.json", availability)
    available = {surface for surface, checks in availability.items() if checks["ready"]}

    if pinned:
        selected = pinned_selection(args.question, pinned, available, args.surface)
    else:
        conversation_event(folder, "planning", "I’m checking which research context fits your question.")

        def session_started(payload: dict) -> None:
            save_json(folder, "planner-session.json", payload)
            if payload.get("agent_view_url"):
                print(f"Planner view: {payload['agent_view_url']}", flush=True)

        def event_received(payload: dict) -> None:
            with (folder / "planner-events.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(payload) + "\n")

        planner_budget = min(40, max(1, args.timeout - (time.monotonic() - started)))
        planner = (
            PydanticExperimentPlanner(model, planner_budget) if args.planner == "openai" else
            HExperimentPlanner(model, int(planner_budget), on_session=session_started, on_event=event_received)
        )
        try:
            selected = select_experiment(args.question, catalogue, available, planner, args.surface)
        except KeyboardInterrupt:
            selected = Selection("blocked", args.question, "The operator interrupted context selection.")
        except PlannerUnavailable as error:
            selected = Selection("blocked", args.question, str(error))
        except Exception as error:
            selected = Selection("blocked", args.question, f"Context selection failed ({type(error).__name__}). Check credentials, model access and connection.")
        save_json(folder, "planning-metrics.json", {"elapsed_seconds": round(time.monotonic() - started, 3), "usage": planner.usage})
    save_json(folder, "selection.json", selected.to_dict())
    print(json.dumps(selected.to_dict(), indent=2, ensure_ascii=False), flush=True)
    conversation_event(folder, "selection", selected.reason, speak=True)
    if selected.status == "blocked" or args.plan_only:
        save_selection_report(folder, selected, args.plan_only)
        return 1 if selected.status == "blocked" else 0

    context = next(item for item in catalogue if item.id == selected.experiment_id)
    target = context.surfaces[selected.surface]
    preflight = checks_payload(check_surface(selected.surface, Path(target.app_path) if target.app_path else None))
    save_json(folder, "preflight.json", preflight)
    remaining = int(args.timeout - (time.monotonic() - started))
    if not preflight["ready"] or remaining < 1:
        reason = "Selection used the execution budget; no session started." if preflight["ready"] else "The selected surface failed preflight; see preflight.json."
        selected = Selection("blocked", args.question, reason)
        save_json(folder, "selection.json", selected.to_dict())
        save_selection_report(folder, selected, False)
        return 1
    save_json(folder, "run.json", {
        **request, "surface": selected.surface, "model": MODEL, "experiment": context.id,
        "title": context.title, "execution_budget_seconds": min(remaining, context.budget_seconds),
    })
    return run_investigation(folder, context, selected.surface, min(remaining, context.budget_seconds), selected.question, args.interactive)


if __name__ == "__main__":
    raise SystemExit(main())
