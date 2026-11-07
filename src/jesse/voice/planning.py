"""Queue spoken questions for the existing plan-only selection workflow."""

import queue
import sys
import threading
from collections.abc import Callable


class VoicePlanningQueue:
    def __init__(self, plan: Callable[[str], int], capacity: int = 4):
        self._plan = plan
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
                print("\nPlanning a spoken question; no H session will start.", flush=True)
                try:
                    result = self._plan(transcript)
                except Exception as error:
                    self._failed = True
                    print(
                        f"Voice planning failed ({type(error).__name__}). "
                        "Check provider access and configuration.",
                        file=sys.stderr,
                        flush=True,
                    )
                else:
                    if result:
                        self._failed = True
                        print(
                            "Voice planning was blocked; inspect the selection and run artifacts.",
                            file=sys.stderr,
                            flush=True,
                        )
            finally:
                self._queue.task_done()

    def close(self) -> bool:
        self._queue.put(None)
        self._worker.join()
        return not self._failed
