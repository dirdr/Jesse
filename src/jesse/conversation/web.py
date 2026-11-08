"""Serve the local Jesse panel; H Agent View opens in a separate window."""
import argparse
import os
from contextlib import asynccontextmanager
from importlib.resources import files
from pathlib import Path
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal

from jesse.research import load_notes
from jesse.personality import PERSONAS, get_persona, run_persona
from .application import RunManager
from .live import cached_frame, live_state
from .speech import cached_action_speech, cached_speech, cached_step_speech, speech_available
from .voice import VoiceListener, voice_unavailable
from .browser_voice import browser_voice_unavailable, create_browser_session


class ResearchQuestion(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class ResearcherMessage(ResearchQuestion):
    event_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    source: Literal["text", "voice"] = "text"


class PersonaSelection(BaseModel):
    id: Literal["pinkman", "plain"]


def create_app(manager: RunManager | None = None, voice: VoiceListener | None = None) -> FastAPI:
    manager = manager or RunManager(Path("runs"))
    voice = voice or VoiceListener(manager, unavailable=lambda: voice_unavailable(needs_planner=False))
    token = secrets.token_urlsafe(32)
    allowed_hosts = {"127.0.0.1", "localhost", "::1", "testserver"}
    allowed_hosts.update(host.strip().lower() for host in os.environ.get("JESSE_ALLOWED_HOSTS", "").split(",") if host.strip())
    public_origin = os.environ.get("JESSE_PUBLIC_URL", "").rstrip("/")

    @asynccontextmanager
    async def lifespan(app):
        yield
        voice.close()
        manager.close()

    app = FastAPI(title="Jesse", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.manager = manager
    assets = Path(str(files(__package__).joinpath("static")))
    app.mount("/static", StaticFiles(directory=assets), name="static")

    @app.middleware("http")
    async def local_requests(request: Request, call_next):
        if request.url.hostname not in allowed_hosts:
            return JSONResponse({"detail": "Use the configured Jesse address."}, status_code=403)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if request.headers.get("x-jesse-token") != token:
                return JSONResponse({"detail": "Refresh the Jesse panel before sending a request."}, status_code=403)
            origin = request.headers.get("origin")
            expected_origin = public_origin or str(request.base_url).rstrip("/")
            if origin and origin.rstrip("/") != expected_origin:
                return JSONResponse({"detail": "Use the configured Jesse panel."}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/healthz")
    def health():
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (assets / "index.html").read_text(encoding="utf-8").replace("__JESSE_TOKEN__", token)

    @app.get("/api/research")
    def research():
        try:
            notes = load_notes(manager.research)
        except ValueError as error:
            raise HTTPException(500, str(error)) from None
        return {"notes": [note.to_dict() for note in notes]}

    @app.get("/api/runs")
    def history():
        return {"runs": manager.history()}

    @app.get("/api/current")
    def current():
        return {"run_id": manager.current_id}

    @app.post("/api/runs", status_code=202)
    def start(body: ResearchQuestion):
        text = body.text.strip()
        if not text:
            raise HTTPException(422, "Enter a research question.")
        try:
            return {"run_id": manager.start(text)}
        except ValueError as error:
            raise HTTPException(409, str(error)) from None

    @app.get("/api/runs/{run_id}")
    def state(run_id: str):
        try:
            return manager.snapshot(run_id)
        except (ValueError, FileNotFoundError):
            raise HTTPException(404, "Investigation not found.") from None

    @app.post("/api/runs/{run_id}/messages")
    def message(run_id: str, body: ResearcherMessage):
        if not body.text.strip():
            raise HTTPException(422, "Enter a message.")
        try:
            return manager.message(run_id, body.event_id, body.text.strip(), body.source)
        except FileNotFoundError:
            raise HTTPException(404, "Investigation not found.") from None
        except ValueError as error:
            raise HTTPException(409, str(error)) from None

    @app.post("/api/runs/{run_id}/stop")
    def stop(run_id: str):
        try:
            return manager.stop(run_id)
        except (ValueError, FileNotFoundError):
            raise HTTPException(404, "Investigation not found.") from None

    @app.get("/api/runs/{run_id}/report", response_class=PlainTextResponse)
    def report(run_id: str):
        try:
            path = manager.folder(run_id) / "report.md"
            return PlainTextResponse(path.read_text(encoding="utf-8"))
        except (ValueError, FileNotFoundError):
            raise HTTPException(404, "Report not available yet.") from None

    @app.get("/api/runs/{run_id}/live")
    def live(run_id: str):
        try:
            return live_state(manager.folder(run_id))
        except (ValueError, FileNotFoundError):
            raise HTTPException(404, "Investigation not found.") from None

    @app.get("/api/runs/{run_id}/frames/{index}")
    def frame(run_id: str, index: int):
        try:
            path = cached_frame(manager.folder(run_id), index)
        except (ValueError, FileNotFoundError):
            raise HTTPException(404, "Investigation not found.") from None
        except Exception:
            raise HTTPException(502, "The screenshot could not be fetched from H.") from None
        if path is None:
            raise HTTPException(404, "Screenshot not available.")
        response = FileResponse(path, media_type="image/jpeg")
        response.headers["Cache-Control"] = "private, max-age=86400, immutable"
        return response

    @app.get("/api/personas")
    def personas():
        return {"selected": manager.persona, "personas": [
            {"id": item.id, "name": item.name, "available": speech_available(item)} for item in PERSONAS.values()]}

    @app.post("/api/persona")
    def select_persona(body: PersonaSelection):
        try:
            manager.select_persona(body.id)
        except ValueError as error:
            raise HTTPException(409, str(error)) from None
        return personas()

    @app.get("/api/speech")
    def speech_state(run_id: str | None = None):
        try:
            persona = run_persona(manager.folder(run_id)) if run_id else get_persona(manager.persona)
        except (ValueError, FileNotFoundError):
            raise HTTPException(404, "Investigation not found.") from None
        return {"available": speech_available(persona)}

    @app.get("/api/runs/{run_id}/speech/{kind}/{index}")
    def indexed_speech(run_id: str, kind: Literal["steps", "actions"], index: int):
        speak = cached_step_speech if kind == "steps" else cached_action_speech
        try:
            folder = manager.folder(run_id)
            if not speech_available(run_persona(folder)):
                raise HTTPException(409, "Configure the speech keys for this run's selected persona.")
            path = speak(folder, index)
        except (ValueError, FileNotFoundError):
            raise HTTPException(404, "Investigation not found.") from None
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(502, "Jesse's voice could not be generated.") from None
        if path is None:
            raise HTTPException(404, "Nothing to say for this item.")
        return FileResponse(path, media_type="audio/mpeg")

    @app.get("/api/runs/{run_id}/speech/{event_id}")
    def speech(run_id: str, event_id: str):
        try:
            folder = manager.folder(run_id)
            if not speech_available(run_persona(folder)):
                raise HTTPException(409, "Configure the speech keys for this run's selected persona.")
            path = cached_speech(folder, event_id)
        except (ValueError, FileNotFoundError):
            raise HTTPException(404, "Investigation not found.") from None
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(502, "Jesse's voice could not be generated.") from None
        if path is None:
            raise HTTPException(404, "Nothing to say for this event.")
        return FileResponse(path, media_type="audio/mpeg")

    @app.get("/api/voice")
    def voice_state():
        return voice.state()

    @app.get("/api/voice/browser")
    def browser_voice_state():
        reason = browser_voice_unavailable()
        return {"available": reason is None, "reason": reason}

    @app.post("/api/voice/session")
    def browser_voice_session():
        try:
            return create_browser_session()
        except ValueError as error:
            raise HTTPException(409, str(error)) from None
        except Exception:
            raise HTTPException(502, "Could not connect to Gladia. Try the microphone again.") from None

    @app.post("/api/voice/turn")
    def browser_voice_turn(body: ResearchQuestion):
        text = body.text.strip()
        if not text:
            raise HTTPException(422, "No speech was detected.")
        return voice.dispatch(text)

    @app.post("/api/voice/start")
    def voice_start():
        try:
            return voice.start()
        except ValueError as error:
            raise HTTPException(409, str(error)) from None

    @app.post("/api/voice/stop")
    def voice_stop():
        return voice.stop()

    return app


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1", help="Bind address; use 0.0.0.0 behind the container frontend")
    parser.add_argument("--surface", choices=("web", "desktop"), default="web", help="Where the agent works: hosted browser or this desktop")
    parser.add_argument("--research", type=Path, help="Folder of research notes (default: ./research or JESSE_RESEARCH_DIR)")
    parser.add_argument("--runs", type=Path, default=Path("runs"), help="Folder for investigations and history (default: ./runs)")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("Use a port between 1024 and 65535")
    try:
        notes = load_notes(args.research)
    except ValueError as error:
        parser.error(str(error))
    import uvicorn
    manager = RunManager(args.runs, research=args.research, surface=args.surface)
    print(f"Open Jesse at http://{args.host}:{args.port} ({len(notes)} research notes, {args.surface}). "
          "H Agent View opens from the panel.", flush=True)
    uvicorn.run(create_app(manager), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
