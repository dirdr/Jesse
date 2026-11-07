"""Serve the local Jesse panel; H Agent View opens in a separate window."""
import argparse
from contextlib import asynccontextmanager
from importlib.resources import files
from pathlib import Path
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal

from jesse.contexts import ContextError, load_contexts
from jesse.personality import PERSONAS, get_persona, run_persona
from .application import RunManager
from .live import cached_frame, live_state
from .speech import cached_action_speech, cached_speech, cached_step_speech, speech_available
from .voice import VoiceListener, voice_unavailable


class ResearchQuestion(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class ResearcherMessage(ResearchQuestion):
    event_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    source: Literal["text", "voice"] = "text"


class PersonaSelection(BaseModel):
    id: Literal["pinkman", "plain"]


def create_app(manager: RunManager | None = None, voice: VoiceListener | None = None) -> FastAPI:
    manager = manager or RunManager(Path("runs"))
    voice = voice or VoiceListener(manager, unavailable=lambda: voice_unavailable(needs_planner=manager.context is None))
    token = secrets.token_urlsafe(32)

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
        if request.url.hostname not in {"127.0.0.1", "localhost", "::1", "testserver"}:
            return JSONResponse({"detail": "Use the local Jesse address."}, status_code=403)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if request.headers.get("x-jesse-token") != token:
                return JSONResponse({"detail": "Refresh the Jesse panel before sending a request."}, status_code=403)
            origin = request.headers.get("origin")
            if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
                return JSONResponse({"detail": "Use the local Jesse panel."}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (assets / "index.html").read_text(encoding="utf-8").replace("__JESSE_TOKEN__", token)

    @app.get("/api/contexts")
    def contexts():
        try:
            items = load_contexts(manager.contexts)
        except ContextError as error:
            raise HTTPException(500, str(error)) from None
        if manager.context:
            items = tuple(item for item in items if item.id == manager.context)
        return {"pinned": manager.context, "contexts": [item.to_dict() for item in items]}

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
    parser.add_argument("--context", help="Run every question in this research context, without the selector")
    parser.add_argument("--surface", choices=("auto", "web", "desktop"), default="auto", help="Execution surface for new investigations")
    parser.add_argument("--contexts", type=Path, help="Folder of research contexts (default: ./contexts or JESSE_CONTEXTS_DIR)")
    parser.add_argument("--runs", type=Path, default=Path("runs"), help="Folder for investigations and history (default: ./runs)")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("Use a port between 1024 and 65535")
    try:
        available = load_contexts(args.contexts)
    except ContextError as error:
        parser.error(str(error))
    if not available:
        parser.error(f"No research contexts found in {args.contexts or 'contexts'}; see contexts/README.md")
    if args.context and args.context not in {item.id for item in available}:
        parser.error(f"Unknown research context {args.context!r}; available: {', '.join(item.id for item in available)}")
    import uvicorn
    manager = RunManager(args.runs, context=args.context, contexts=args.contexts, surface=args.surface)
    scope = f"context {args.context}" if args.context else f"{len(available)} research contexts"
    print(f"Open Jesse at http://127.0.0.1:{args.port} ({scope}). H Agent View opens from the panel.", flush=True)
    uvicorn.run(create_app(manager), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
