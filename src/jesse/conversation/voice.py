"""Listen to the local microphone through Gladia and turn each spoken turn into a run or a correction."""
import os
import queue
import threading
from collections.abc import Callable
from uuid import uuid4

from .application import RunManager

MAX_TURNS = 20
Listen = Callable[[Callable[[str], None], Callable[[str], None], threading.Event], None]


def gladia_listen(on_turn, on_partial, stopping: threading.Event) -> None:
    """Run the Gladia live preview until `stopping` is set; the last turn is still delivered."""
    import sounddevice
    from gladiaio_sdk import GladiaClient
    from jesse.voice.live import run_live_preview

    class StoppableStream:
        def __init__(self, **options):
            self.stream = sounddevice.RawInputStream(**options)

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *exc):
            return self.stream.__exit__(*exc)

        def read(self, frames):
            # run_live_preview treats KeyboardInterrupt as "stop listening and flush final transcripts".
            if stopping.is_set():
                raise KeyboardInterrupt
            return self.stream.read(frames)

    run_live_preview(GladiaClient(), StoppableStream, on_turn=on_turn, on_partial=on_partial)


def voice_unavailable() -> str | None:
    if not os.environ.get("GLADIA_API_KEY", "").strip():
        return "Set GLADIA_API_KEY in .env to use the microphone."
    if not any(os.environ.get(name, "").strip() for name in ("OPENAI_API_KEY", "OPENAI_KEY")):
        return "Set OPENAI_API_KEY or OPENAI_KEY in .env: spoken questions go to the experiment selector."
    try:
        import sounddevice  # noqa: F401
    except OSError:
        return "PortAudio is missing; install it to use the microphone."
    return None


class VoiceListener:
    def __init__(self, manager: RunManager, *, listen: Listen = gladia_listen, unavailable=voice_unavailable):
        self.manager = manager
        self.listen = listen
        self.unavailable = unavailable
        self.lock = threading.Lock()
        self.stopping = threading.Event()
        self.thread: threading.Thread | None = None
        self.partial = ""
        self.error: str | None = None
        self.turns: list[dict] = []

    @property
    def listening(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def state(self) -> dict:
        with self.lock:
            return {"available": self.unavailable() is None, "reason": self.unavailable(),
                    "listening": self.listening and not self.stopping.is_set(),
                    "partial": self.partial, "error": self.error, "turns": list(self.turns)}

    def start(self) -> dict:
        reason = self.unavailable()
        if reason:
            raise ValueError(reason)
        with self.lock:
            if not self.listening:
                self.stopping.clear()
                self.error = None
                self.partial = ""
                self.thread = threading.Thread(target=self._run, name="jesse-voice", daemon=True)
                self.thread.start()
        return self.state()

    def stop(self) -> dict:
        self.stopping.set()
        return self.state()

    def close(self, timeout: float = 10) -> None:
        self.stopping.set()
        if self.thread is not None:
            self.thread.join(timeout)

    def _run(self) -> None:
        # Gladia calls on_turn on the capture thread; dispatch elsewhere so audio keeps flowing.
        turns: queue.Queue[str | None] = queue.Queue()
        worker = threading.Thread(target=self._drain, args=(turns,), name="jesse-voice-turns", daemon=True)
        worker.start()
        try:
            self.listen(turns.put, self._on_partial, self.stopping)
        except Exception as error:
            with self.lock:
                self.error = f"Microphone stopped: {error}"
        finally:
            turns.put(None)
            worker.join()
            with self.lock:
                self.partial = ""

    def _on_partial(self, text: str) -> None:
        with self.lock:
            self.partial = text

    def _drain(self, turns: "queue.Queue[str | None]") -> None:
        while (text := turns.get()) is not None:
            with self.lock:
                self.partial = ""
            self.dispatch(text)

    def dispatch(self, text: str) -> dict:
        """Steer the active investigation if it accepts messages; otherwise start a new one."""
        turn = {"id": uuid4().hex, "text": text, "action": "failed", "run_id": None, "detail": None}
        try:
            run_id = self.manager.current_id
            snapshot = self.manager.snapshot(run_id) if run_id else None
            if snapshot and snapshot["active"]:
                if not snapshot["can_message"]:
                    raise ValueError("Wait for the laboratory session to open before speaking a correction.")
                self.manager.message(run_id, turn["id"], text, "voice")
                turn.update(action="steered", run_id=run_id)
            else:
                turn.update(action="started", run_id=self.manager.start(text))
        except Exception as error:
            turn["detail"] = str(error) or type(error).__name__
        with self.lock:
            self.turns = [*self.turns, turn][-MAX_TURNS:]
        return turn
