"""Research question + the researcher's notes → one semi-autonomous lab investigation."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from jesse.personality import get_persona
from jesse.preflight import check_surface, checks_payload
from jesse.research import BUDGET_SECONDS, load_notes
from jesse.runtime import save_json
from .runner import MODEL, run_investigation


def blocked(folder: Path, reason: str) -> int:
    save_json(folder, "outcome.json", {"outcome": "blocked", "reason": reason})
    (folder / "report.md").write_text(f"# Investigation report\n\nOutcome: **blocked**\n\n{reason}\n", encoding="utf-8")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", help="Research question")
    parser.add_argument("--notes", action="store_true", help="List the research notes Jesse will read, then exit")
    parser.add_argument("--research", type=Path, help="Folder of research notes (default: ./research or JESSE_RESEARCH_DIR)")
    parser.add_argument("--surface", choices=("web", "desktop"), default="web")
    parser.add_argument("--timeout", type=int, default=BUDGET_SECONDS, metavar="SECONDS")
    parser.add_argument("--interactive", action="store_true", help="Keep the session open for corrections and follow-ups")
    parser.add_argument("--run-dir", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        notes = load_notes(args.research)
    except ValueError as error:
        parser.error(str(error))
    if args.notes:
        print(json.dumps([note.to_dict() for note in notes], indent=2, ensure_ascii=False))
        return 0
    if not args.question or not 1 <= len(args.question.strip()) <= 4000:
        parser.error("Supply a research question of 1–4000 characters, or use --notes")
    if not 1 <= args.timeout <= BUDGET_SECONDS:
        parser.error(f"--timeout must be between 1 and {BUDGET_SECONDS} seconds")

    folder = args.run_dir or Path("runs") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    if args.run_dir is not None and (folder / "request.json").exists():
        parser.error("The supplied run directory already contains an investigation")
    folder.mkdir(parents=True, exist_ok=args.run_dir is not None)
    if not (folder / "persona.json").exists():
        save_json(folder, "persona.json", {"id": get_persona().id})
    print(f"Artifacts: {folder}", flush=True)
    request = {"run_id": folder.name, "question": args.question, "surface": args.surface,
               "notes": [note.to_dict() for note in notes], "budget_seconds": args.timeout,
               "started_at": datetime.now(timezone.utc).isoformat()}
    save_json(folder, "request.json", request)
    preflight = checks_payload(check_surface(args.surface))
    save_json(folder, "preflight.json", preflight)
    if not preflight["ready"]:
        return blocked(folder, f"The {args.surface} surface is not ready; see preflight.json.")
    save_json(folder, "run.json", {**request, "model": MODEL, "title": args.question.strip()[:120]})
    return run_investigation(folder, notes, args.surface, args.timeout, args.question, args.interactive)


if __name__ == "__main__":
    raise SystemExit(main())
