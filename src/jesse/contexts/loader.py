"""Read context folders: context.toml, protocol.md and an optional tools.py."""
import importlib.util
import os
from pathlib import Path
import re
import tomllib
from types import ModuleType

from .domain import BUILTIN_TOOLS, SURFACE_KINDS, ContextError, ResearchContext, Surface

CONTEXT_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")


def default_root() -> Path:
    return Path(os.environ.get("JESSE_CONTEXTS_DIR") or "contexts")


def _strings(data: dict, key: str, source: Path, required: bool = False) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ContextError(f"{source}: {key} must be a list of non-empty strings")
    if required and not value:
        raise ContextError(f"{source}: {key} needs at least one entry")
    return tuple(item.strip() for item in value)


def _text(data: dict, key: str, source: Path, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ContextError(f"{source}: {key} must be a non-empty string")
    return value.strip()


def _bounded(data: dict, key: str, source: Path, default: int, low: int, high: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ContextError(f"{source}: limits.{key} must be an integer from {low} to {high}")
    return value


def _surfaces(data: dict, source: Path) -> dict[str, Surface]:
    declared = data.get("surfaces")
    if not isinstance(declared, dict) or not declared:
        raise ContextError(f"{source}: declare at least one [surfaces.web] or [surfaces.desktop] table")
    surfaces = {}
    for kind, options in declared.items():
        if kind not in SURFACE_KINDS or not isinstance(options, dict):
            raise ContextError(f"{source}: unknown surface {kind!r}; use web or desktop")
        if kind == "web":
            url = _text(options, "start_url", source)
            if not url.startswith("https://"):
                raise ContextError(f"{source}: surfaces.web.start_url must be an https URL")
            width = _bounded(options, "width", source, 1280, 640, 2560)
            height = _bounded(options, "height", source, 900, 480, 1600)
            surfaces[kind] = Surface("web", start_url=url, width=width, height=height)
        else:
            app_path = options.get("app_path")
            if app_path is not None and (not isinstance(app_path, str) or not app_path.strip()):
                raise ContextError(f"{source}: surfaces.desktop.app_path must be a non-empty string")
            surfaces[kind] = Surface("desktop", app_path=app_path)
    return surfaces


def load_context(folder: Path) -> ResearchContext:
    source = folder / "context.toml"
    try:
        data = tomllib.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ContextError(f"{folder}: missing context.toml") from None
    except tomllib.TOMLDecodeError as error:
        raise ContextError(f"{source}: {error}") from None
    context_id = _text(data, "id", source)
    if not CONTEXT_ID.fullmatch(context_id):
        raise ContextError(f"{source}: id must use lowercase letters, digits and hyphens")
    protocol_path = folder / "protocol.md"
    if not protocol_path.is_file():
        raise ContextError(f"{folder}: missing protocol.md")
    limits = data.get("limits", {})
    if not isinstance(limits, dict):
        raise ContextError(f"{source}: [limits] must be a table")
    tools = _strings(data, "tools", source) if "tools" in data else ("publish_update", "acknowledge_researcher_message", "record_observation")
    unknown = set(tools) - BUILTIN_TOOLS
    if unknown:
        raise ContextError(f"{source}: unknown built-in tools {sorted(unknown)}; custom tools belong in tools.py")
    extension = folder / "tools.py"
    return ResearchContext(
        id=context_id, title=_text(data, "title", source), application=_text(data, "application", source),
        activity=_text(data, "activity", source, data.get("title")), questions=_strings(data, "questions", source, True),
        surfaces=_surfaces(data, source), protocol=protocol_path.read_text(encoding="utf-8"), folder=folder.resolve(),
        unsupported=_strings(data, "unsupported", source), assumptions=_strings(data, "assumptions", source),
        completion=_strings(data, "completion", source), sources=_strings(data, "sources", source),
        status=_text(data, "status", source, "unverified"),
        budget_seconds=_bounded(limits, "budget_seconds", source, 600, 30, 600),
        max_steps=_bounded(limits, "max_steps", source, 110, 1, 300),
        max_trials=_bounded(limits, "max_trials", source, 2, 1, 20),
        tools=tools, extension=extension if extension.is_file() else None,
    )


def load_contexts(root: Path | None = None) -> tuple[ResearchContext, ...]:
    root = root or default_root()
    if not root.is_dir():
        return ()
    contexts = [load_context(folder) for folder in sorted(root.iterdir())
                if folder.is_dir() and not folder.name.startswith(("_", ".")) and (folder / "context.toml").exists()]
    ids = [context.id for context in contexts]
    duplicates = {item for item in ids if ids.count(item) > 1}
    if duplicates:
        raise ContextError(f"{root}: duplicate context ids {sorted(duplicates)}")
    return tuple(contexts)


def find_context(context_id: str, root: Path | None = None) -> ResearchContext:
    for context in load_contexts(root):
        if context.id == context_id:
            return context
    raise ContextError(f"No research context {context_id!r} in {root or default_root()}")


def load_extension(context: ResearchContext) -> ModuleType | None:
    if context.extension is None:
        return None
    spec = importlib.util.spec_from_file_location(f"jesse_context_{context.id.replace('-', '_')}", context.extension)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
