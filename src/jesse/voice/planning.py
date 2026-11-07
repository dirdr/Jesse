"""Queue spoken questions for the existing plan-only selection workflow."""

import queue
import sys
import threading
from collections.abc import Callable


class VoicePlanningQueue:
    def __init__(self, plan: Callable[[str], int], capacity: int = 4, *, operation: str = "planning"):
        self._plan = plan
        self._operation = operation
        self._queue: queue.Queue[str | None] = queue.Queue(maxsize=capacity)
        self._failed = False
        self._worker = threading.Thread(target=self._run, name="voice-planner")
        self._worker.start()

    def submit(self, transcript: str) -> None:
        try:
            self._queue.put_nowait(transcript)
        except queue.Full as error:
            raise RuntimeError(
                "Voice planning queue is full; this turn was not submitted."
            ) from error

    def _run(self) -> None:
        while True:
            transcript = self._queue.get()
            try:
                if transcript is None:
                    return
                if self._operation == "planning":
                    print("\nPlanning a spoken question; no H session will start.", flush=True)
                else:
                    print(f"\nProcessing spoken question: {self._operation}.", flush=True)
                try:
                    result = self._plan(transcript)
                except Exception as error:
                    self._failed = True
                    print(
                        f"Voice {self._operation} failed ({type(error).__name__}). "
                        "Check provider access and configuration.",
                        file=sys.stderr,
                        flush=True,
                    )
                else:
                    if result:
                        self._failed = True
                        print(
                            f"Voice {self._operation} was blocked; inspect the run artifacts.",
                            file=sys.stderr,
                            flush=True,
                        )
            finally:
                self._queue.task_done()

    def close(self) -> bool:
        self._queue.put(None)
        self._worker.join()
        return not self._failed
