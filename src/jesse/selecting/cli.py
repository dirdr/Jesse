"""Research question → catalogue selection → bounded computer-use experiment."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from jesse.experiments.netlogo.cli import run_ready_experiment
from jesse.experiments.netlogo.preflight import check_desktop, checks_payload
from jesse.experiments.coolant.cli import run_ready_experiment as run_coolant_experiment
from jesse.runtime import conversation_event
from .adapters import HExperimentPlanner, PydanticExperimentPlanner
from .application import select_experiment
from .domain import CATALOGUE, PlannerUnavailable, Selection


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", help="Research question to match against supported protocols")
    parser.add_argument("--catalogue", action="store_true", help="List protocol capabilities without calling an API")
    parser.add_argument("--surface", choices=("auto", "web", "desktop"), default="auto")
    parser.add_argument("--planner", choices=("openai", "h"), default="openai")
    parser.add_argument("--planner-model", help="Provider model; defaults to OPENAI_MODEL/gpt-5-mini or holo4-27b")
    parser.add_argument("--plan-only", action="store_true", help="Select a protocol without operating scientific software")
    parser.add_argument("--timeout", type=int, default=300, metavar="SECONDS", help="Shared selection and execution budget, 1–600 seconds")
    parser.add_argument("--netlogo", type=Path, help="Optional installed NetLogo .app path")
    parser.add_argument("--interactive", action="store_true", help="Keep supported sessions open for bounded conversation")
    parser.add_argument("--run-dir", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.catalogue:
        print(json.dumps([item.to_dict() for item in CATALOGUE], indent=2))
        return 0
    if args.question is None:
        parser.error("Supply a research question or use --catalogue")
    if not 1 <= args.timeout <= 600:
        parser.error("--timeout must be between 1 and 600 seconds")

    started = time.monotonic()
    folder = args.run_dir or Path("runs") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    if args.run_dir is not None and (folder / "request.json").exists():
        parser.error("The supplied run directory already contains an investigation")
    folder.mkdir(parents=True, exist_ok=args.run_dir is not None)
    print(f"Artifacts: {folder}", flush=True)
    conversation_event(folder, "planning", "I’m checking which supported experiment fits your question.")
    model = args.planner_model or (os.environ.get("OPENAI_MODEL", "gpt-5-mini") if args.planner == "openai" else "holo4-27b")
    request = {"run_id": folder.name, "question": args.question, "surface_preference": args.surface,
               "planner": args.planner, "planner_model": model, "budget_seconds": args.timeout}
    save_json(folder, "request.json", request)
    save_json(folder, "catalogue.json", [item.to_dict() for item in CATALOGUE])
    availability = {}
    application = None
    for surface in ("web", "desktop"):
        checks, found_application = check_desktop(args.netlogo, surface)
        availability[surface] = checks_payload(checks)
        application = application or found_application
    save_json(folder, "availability.json", availability)
    available = {surface for surface, checks in availability.items() if checks["ready"]}

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
        selected = select_experiment(args.question, CATALOGUE, available, planner, args.surface)
    except KeyboardInterrupt:
        selected = Selection("blocked", args.question, "The operator interrupted catalogue selection.")
    except PlannerUnavailable as error:
        selected = Selection("blocked", args.question, str(error))
    except ValueError as error:
        selected = Selection("blocked", args.question, f"Catalogue selection failed: {error}")
    except Exception as error:
        selected = Selection("blocked", args.question, f"Catalogue selection failed ({type(error).__name__}). Check credentials, model access and connection.")
    save_json(folder, "selection.json", selected.to_dict())
    save_json(folder, "planning-metrics.json", {"elapsed_seconds": round(time.monotonic() - started, 3), "usage": planner.usage})
    print(json.dumps(selected.to_dict(), indent=2, ensure_ascii=False), flush=True)
    conversation_event(folder, "selection", selected.reason, speak=True)
    if selected.status == "blocked" or args.plan_only:
        save_selection_report(folder, selected, args.plan_only)
        return 1 if selected.status == "blocked" else 0

    remaining = int(args.timeout - (time.monotonic() - started))
    if remaining < 1:
        save_selection_report(folder, selected, True)
        print("Selection used the execution budget; no simulator session started.")
        return 1
    # Explicit dispatch keeps a catalogue entry from importing arbitrary code.
    if selected.experiment_id not in {"netlogo-enzyme-feasibility", "chemcollective-coolant-feasibility"}:
        selected = Selection("blocked", args.question, "No approved executor is registered for this protocol.")
        save_json(folder, "selection.json", selected.to_dict())
        save_selection_report(folder, selected, False)
        return 1
    save_json(folder, "run.json", {
        **request, "surface": selected.surface, "model": "holo4-27b",
        "experiment": selected.experiment_id, "execution_budget_seconds": remaining,
    })
    save_json(folder, "preflight.json", availability[selected.surface])
    if selected.experiment_id == "chemcollective-coolant-feasibility":
        return run_coolant_experiment(folder, remaining, selected.question, args.interactive)
    return run_ready_experiment(folder, remaining, str(application) if application else None, selected.surface, selected.question)


if __name__ == "__main__":
    raise SystemExit(main())
