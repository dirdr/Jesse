"""Run a bounded, experimental ChemCollective coolant investigation."""
import argparse
from datetime import datetime, timezone
import multiprocessing
from pathlib import Path

from jesse.experiments.netlogo.preflight import check_desktop, checks_payload
from jesse.runtime import save_json, stop_worker
from .domain import DEFAULT_QUESTION, build_prompt
from .runner import CoolantRecords, execute


def run_ready_experiment(folder: Path, budget_seconds: int, question: str = DEFAULT_QUESTION, interactive: bool = False) -> int:
    if not 1 <= budget_seconds <= 600:
        raise ValueError("Execution budget must be between 1 and 600 seconds")
    records = CoolantRecords(folder)
    (folder / "protocol.md").write_text(build_prompt(question), encoding="utf-8")
    worker = multiprocessing.get_context("spawn").Process(target=execute, args=(folder, budget_seconds, interactive))
    try:
        worker.start()
        worker.join(budget_seconds)
        if worker.is_alive():
            stop_worker(worker)
            records.finish("Run budget exhausted; operator stopped and earlier evidence retained.")
            return 1
    except KeyboardInterrupt:
        stop_worker(worker)
        records.finish("Stopped by the researcher; earlier evidence retained.")
        return 130
    if not (folder / "outcome.json").exists():
        records.finish("Worker exited unexpectedly; inspect saved events.")
        return 1
    import json
    return 1 if json.loads((folder / "outcome.json").read_text())["outcome"] == "blocked" else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("--check", action="store_true", help="Check local setup without an API call")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--interactive", action="store_true", help="Keep the H session open for bounded follow-ups")
    args = parser.parse_args(argv)
    if not 1 <= args.timeout <= 600 or not 1 <= len(args.question.strip()) <= 4000:
        parser.error("Supply a 1–4000 character question and a 1–600 second budget")
    checks, _ = check_desktop(surface="web")
    preflight = checks_payload(checks)
    if args.check:
        import json
        print(json.dumps(preflight, indent=2))
        return 0 if preflight["ready"] else 1
    folder = Path("runs") / ("coolant-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    folder.mkdir(parents=True)
    save_json(folder, "run.json", {"experiment": "chemcollective-coolant-feasibility", "surface": "web", "question": args.question, "budget_seconds": args.timeout})
    save_json(folder, "preflight.json", preflight)
    print(f"Artifacts: {folder}", flush=True)
    if not preflight["ready"]:
        CoolantRecords(folder).finish("Hosted-browser preflight failed; check HAI_API_KEY and dependencies.")
        return 1
    return run_ready_experiment(folder, args.timeout, args.question, args.interactive)


if __name__ == "__main__":
    raise SystemExit(main())
