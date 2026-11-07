"""Analyze a saved NetLogo run without API calls or simulator access."""
import argparse
import json
from pathlib import Path

from .adapters import FileAnalysisRecords
from .application import analyze_measurements


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args(argv)
    try:
        analysis = analyze_measurements(FileAnalysisRecords(args.run_directory))
    except (ValueError, TypeError, OSError) as error:
        parser.exit(1, f"Cannot analyze run: {error}\n")
    print(json.dumps(analysis, indent=2, allow_nan=False))
    print(f"Report: {args.run_directory / 'analyses' / (analysis['analysis_id'] + '.md')}")
    return 0 if analysis["status"] == "compared" else 1


if __name__ == "__main__":
    raise SystemExit(main())
