"""CLI composition root and bounded desktop process lifecycle."""
import argparse
from datetime import datetime, timezone
import json
import multiprocessing
from pathlib import Path
import signal
import sys

from .adapters import FileExperimentRecords, HDesktopAgent
from .application import run_experiment
from .preflight import check_desktop, checks_payload


def execute(folder: Path, budget_seconds: int, application: str | None, surface: str) -> None:
    records = FileExperimentRecords(folder)
    try:
        instructions = (folder / "protocol.md").read_text(encoding="utf-8")
        outcome = run_experiment(HDesktopAgent(budget_seconds, surface=surface), records, instructions)
        if outcome == "blocked":
            raise SystemExit(1)
    except KeyboardInterrupt:
        records.finish("inconclusive", "The operator interrupted the run. Earlier evidence is retained.")
        raise SystemExit(130)
    except TimeoutError:
        records.finish("inconclusive", "The desktop wait exceeded its budget. Earlier evidence is retained.")
        raise SystemExit(1)
    except Exception as error:
        # Provider exception messages may include request details. Persist the type,
        # not credentials or arbitrary request bodies, in the operator diagnostic.
        (folder / "error.json").write_text(json.dumps({"type": type(error).__name__}), encoding="utf-8")
        records.finish("blocked", f"Desktop execution failed ({type(error).__name__}). Check connection, credentials and desktop permissions; prior evidence is retained.")
        raise SystemExit(1)


def stop_worker(process: multiprocessing.Process) -> None:
    if process.is_alive():
        # SIGINT lets the SDK adapter cancel the session before closing its bridge.
        import os
        try:
            os.kill(process.pid, signal.SIGINT)
        except ProcessLookupError:
            pass
        process.join(3)
    if process.is_alive():
        process.terminate()
        process.join(2)
    if process.is_alive():
        process.kill()
        process.join(2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded NetLogo desktop feasibility test")
    parser.add_argument("--check", action="store_true", help="Check setup without creating an H session or controlling the desktop")
    parser.add_argument("--surface", choices=("desktop", "web"), default="desktop", help="Native application or hosted visual browser")
    parser.add_argument("--netlogo", type=Path, help="Installed NetLogo .app bundle outside standard folders")
    parser.add_argument("--timeout", type=int, default=600, metavar="SECONDS", help="Run budget, 1–600 seconds (default: 600)")
    args = parser.parse_args(argv)
    if not 1 <= args.timeout <= 600:
        parser.error("--timeout must be between 1 and 600 seconds")
    checks, application = check_desktop(args.netlogo, args.surface)
    preflight = checks_payload(checks)
    if args.check:
        print(json.dumps(preflight, indent=2))
        return 0 if preflight["ready"] else 1

    folder = Path("runs") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    records = FileExperimentRecords(folder)
    (folder / "run.json").write_text(json.dumps({
        "run_id": folder.name, "surface": args.surface, "model": "holo4-27b",
        "experiment": "netlogo-enzyme-feasibility", "budget_seconds": args.timeout,
    }, indent=2), encoding="utf-8")
    print(f"Artifacts: {folder}", flush=True)
    (folder / "preflight.json").write_text(json.dumps(preflight, indent=2), encoding="utf-8")
    if not preflight["ready"]:
        reason = " ".join(f"{check.name}: {check.detail}" for check in checks if not check.ready)
        records.finish("blocked", reason)
        print(f"Blocked: {reason}")
        return 1

    return run_ready_experiment(folder, args.timeout, str(application) if application else None, args.surface)


def run_ready_experiment(folder: Path, budget_seconds: int, application_path: str | None, surface: str, question: str | None = None) -> int:
    """Execute an already selected/preflighted protocol in the same run folder."""
    if not 1 <= budget_seconds <= 600 or surface not in {"desktop", "web"}:
        raise ValueError("Invalid execution budget or surface")
    records = FileExperimentRecords(folder)
    from .domain import build_prompt
    (folder / "protocol.md").write_text(build_prompt(surface, application_path, question), encoding="utf-8")
    process = multiprocessing.get_context("spawn").Process(target=execute, args=(folder, budget_seconds, application_path, surface))
    try:
        process.start()
        process.join(budget_seconds)
        if process.is_alive():
            stop_worker(process)
            records.finish("inconclusive", "Run budget exhausted; desktop worker stopped. Earlier evidence is retained.")
            return 1
    except KeyboardInterrupt:
        stop_worker(process)
        records.finish("inconclusive", "Stopped by the operator. Earlier evidence is retained.")
        return 130
    if process.exitcode and not (folder / "outcome.json").exists():
        records.finish("blocked", "Desktop worker exited unexpectedly. Inspect retained events and session metadata.")
    print(f"Report: {folder / 'report.md'}")
    return 0 if process.exitcode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
