"""Live view of an H session from its persisted events: screens, actions, plan and measurements.

Only the agent's visible message (`content`) is exposed; private reasoning is never projected.
Screenshots stay on H's platform and are fetched with the local API key, then cached in the run.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlparse

# Action arguments worth showing; everything else (evidence lists, long reports) stays in the run files.
ACTION_FIELDS = ("x", "y", "element", "content", "keys", "seconds", "zoom_factor", "url", "direction",
                 "trial_id", "observation_id", "value", "unit", "volume", "final_c", "status")
HIDDEN_TOOLS = {"answer"}
SCREENSHOT_HOST_SUFFIX = ".hcompany.ai"


def _read_events(folder: Path) -> list[dict]:
    path = folder / "events.jsonl"
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # the writer may be mid-line
    return events


def _short(value, limit=160):
    if isinstance(value, str) and len(value) > limit:
        return value[: limit - 1] + "…"
    return value


def _legacy_display(folder: Path, reading: dict) -> dict:
    analysis_path = folder / f"analysis-{reading.get('trial_id')}.json"
    try:
        analysis = json.loads(analysis_path.read_text(encoding="utf-8")) if analysis_path.exists() else {}
    except (OSError, json.JSONDecodeError):
        analysis = {}
    value = analysis.get("specific_heat_j_g_c")
    return {"fields": {"Coolant": f"{reading.get('coolant_volume_ml')} mL at {reading.get('coolant_initial_c')} °C",
                       "Water": f"{reading.get('water_volume_ml')} mL at {reading.get('water_initial_c')} °C",
                       "Final": f"{reading.get('final_c')} °C"},
            "result": f"{value:.3f} J/(g·°C)" if value is not None else None,
            "status": analysis.get("status", "recorded")}


def _measurements(folder: Path) -> list[dict]:
    rows = []
    for path in sorted((folder / "observations").glob("*.json")) if (folder / "observations").is_dir() else []:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        display = payload.get("display")
        if display is None and "reading" in payload:
            display = _legacy_display(folder, payload["reading"])
        if display is None:
            continue
        rows.append({"id": payload.get("trial_id") or payload.get("reading", {}).get("trial_id") or path.stem,
                     "at": payload.get("recorded_at"), "fields": display.get("fields") or {},
                     "result": display.get("result"), "status": display.get("status", "recorded")})
    return rows


def live_state(folder: Path) -> dict:
    frames, actions, plan = [], [], []
    steps = cost = None
    errors = 0
    for event in _read_events(folder):
        data = event.get("data") or {}
        kind = data.get("kind")
        if kind == "observation_event":
            image = data.get("image") or {}
            if image.get("type") == "url" and image.get("source"):
                meta = data.get("metadata") or {}
                frames.append({"index": len(frames), "at": event.get("timestamp"),
                               "viewport": meta.get("viewport_size"), "cursor": meta.get("cursor_position")})
        elif kind == "policy_event":
            text = (data.get("content") or "").strip()
            for request in data.get("tool_reqs") or []:
                name = request.get("tool_name", "")
                if name in HIDDEN_TOOLS:
                    continue
                args = request.get("args") or {}
                if name == "update_plan":
                    plan = [{"title": _short(goal.get("title", ""), 200), "status": goal.get("status", "pending")}
                            for goal in args.get("goals") or []]
                actions.append({"index": len(actions), "at": event.get("timestamp"), "tool": name,
                                "frame": len(frames) - 1 if frames else None, "text": _short(text, 400),
                                "args": {key: _short(args[key]) for key in ACTION_FIELDS if key in args}})
            if not data.get("tool_reqs") and text:
                actions.append({"index": len(actions), "at": event.get("timestamp"), "tool": "message",
                                "frame": len(frames) - 1 if frames else None, "text": _short(text, 400), "args": {}})
        elif kind == "error_event":
            errors += 1
        elif event.get("type") == "MetricsUpdateEvent":
            metrics = data.get("metrics") or {}
            steps = metrics.get("steps", steps)
            cost = metrics.get("total_cost", cost)
    return {"frames": frames, "actions": actions, "plan": plan, "measurements": _measurements(folder),
            "steps": steps, "cost_usd": cost, "errors": errors}


def frame_source(folder: Path, index: int) -> str | None:
    count = -1
    for event in _read_events(folder):
        data = event.get("data") or {}
        image = data.get("image") or {}
        if data.get("kind") == "observation_event" and image.get("type") == "url" and image.get("source"):
            count += 1
            if count == index:
                return image["source"]
    return None


def cached_frame(folder: Path, index: int, fetch=None) -> Path | None:
    """Return a local copy of screenshot `index`, fetching it from H once."""
    if index < 0:
        return None
    cache = folder / "frames" / f"{index:05d}.jpg"
    if cache.is_file():
        return cache
    source = frame_source(folder, index)
    if source is None:
        return None
    host = urlparse(source).hostname or ""
    if urlparse(source).scheme != "https" or not host.endswith(SCREENSHOT_HOST_SUFFIX):
        return None
    content = (fetch or _fetch)(source)
    cache.parent.mkdir(exist_ok=True)
    temporary = cache.with_suffix(".tmp")
    temporary.write_bytes(content)
    temporary.replace(cache)
    return cache


def _fetch(url: str) -> bytes:
    import httpx

    key = os.environ.get("HAI_API_KEY")
    if not key:
        raise PermissionError("HAI_API_KEY is not set for the Jesse panel")
    with httpx.Client(follow_redirects=True, timeout=20, headers={"Authorization": f"Bearer {key}"}) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content
