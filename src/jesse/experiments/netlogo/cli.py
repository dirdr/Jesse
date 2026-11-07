"""Composition root and bounded desktop process lifecycle."""
import multiprocessing
import os
from pathlib import Path
from datetime import datetime, timezone
from .application import run_experiment
from .adapters import HDesktopAgent, FileExperimentRecords

def execute(folder: Path) -> None:
    run_experiment(HDesktopAgent(), FileExperimentRecords(folder))

def main():
    folder = Path('runs') / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True)
    if not os.environ.get('HAI_API_KEY'):
        (folder / 'report.md').write_text('# Blocked\n\nSet HAI_API_KEY in the environment.\n')
        print('Blocked: set HAI_API_KEY. No desktop session started.')
        return 1
    process = multiprocessing.Process(target=execute, args=(folder,))
    process.start()
    process.join(600)
    if process.is_alive():
        process.terminate()
        process.join()
        (folder / 'report.md').write_text('# Inconclusive\n\nTen-minute session limit reached; desktop connection closed.\n')
        return 1
    if process.exitcode:
        (folder / 'report.md').write_text('# Blocked\n\nSession failed. Inspect terminal error for SDK, API or macOS Screen Recording/Accessibility permissions.\n')
        return 1
    print(f'Artifacts: {folder}')
    return 0



