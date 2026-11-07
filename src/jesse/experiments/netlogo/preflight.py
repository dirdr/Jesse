"""Read-only checks before starting a paid session or moving the desktop."""
from dataclasses import asdict, dataclass
import importlib.util
import os
from pathlib import Path
import sys


@dataclass(frozen=True)
class Check:
    name: str
    ready: bool
    detail: str


def find_netlogo(explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        path = explicit.expanduser().resolve()
        return path if path.is_dir() and path.suffix == ".app" else None
    for root in (Path("/Applications"), Path.home() / "Applications"):
        if not root.exists():
            continue
        for pattern in ("*NetLogo*.app", "*NetLogo*/*NetLogo*.app"):
            for path in sorted(root.glob(pattern)):
                if "3d" not in path.name.lower():
                    return path
    return None


def check_desktop(explicit: Path | None = None, surface: str = "desktop") -> tuple[list[Check], Path | None]:
    application = find_netlogo(explicit)
    checks = [
        Check("credentials", bool(os.environ.get("HAI_API_KEY", "").strip()), "HAI_API_KEY must be supplied through the environment; its value is never printed."),
        Check("sdk", importlib.util.find_spec("hai_agents") is not None, "Install project dependencies with uv sync."),
    ]
    if surface == "web":
        return checks, None
    checks.append(Check("netlogo", application is not None, str(application) if application else "NetLogo Desktop not found; install it or pass --netlogo /path/to/NetLogo.app."))
    if sys.platform != "darwin":
        checks.append(Check("desktop_permissions", False, "This feasibility runner currently verifies macOS permissions only."))
        return checks, application
    try:
        import Quartz
        from ApplicationServices import AXIsProcessTrusted
        checks.extend([
            Check("screen_recording", bool(Quartz.CGPreflightScreenCaptureAccess()), "Enable Screen Recording for the launching terminal/app in macOS System Settings, then restart it."),
            Check("accessibility", bool(AXIsProcessTrusted()), "Enable Accessibility for the launching terminal/app in macOS System Settings, then restart it."),
        ])
    except ImportError:
        checks.append(Check("desktop_permissions", False, "Desktop permission checks require the SDK desktop dependencies; run uv sync."))
    return checks, application


def checks_payload(checks: list[Check]) -> dict:
    return {"ready": all(check.ready for check in checks), "checks": [asdict(check) for check in checks]}
