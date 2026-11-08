"""Read-only checks before starting a paid session or moving the desktop."""
from dataclasses import asdict, dataclass
import importlib.util
import os
import sys


@dataclass(frozen=True)
class Check:
    name: str
    ready: bool
    detail: str


def check_surface(surface: str) -> list[Check]:
    checks = [
        Check("credentials", bool(os.environ.get("HAI_API_KEY", "").strip()), "HAI_API_KEY must be supplied through the environment; its value is never printed."),
        Check("sdk", importlib.util.find_spec("hai_agents") is not None, "Install project dependencies with uv sync."),
    ]
    if surface == "web":
        return checks
    if sys.platform != "darwin":
        checks.append(Check("desktop_permissions", False, "Desktop runs currently verify macOS permissions only."))
        return checks
    try:
        import Quartz
        from ApplicationServices import AXIsProcessTrusted
        checks.extend([
            Check("screen_recording", bool(Quartz.CGPreflightScreenCaptureAccess()), "Enable Screen Recording for the launching terminal/app in macOS System Settings, then restart it."),
            Check("accessibility", bool(AXIsProcessTrusted()), "Enable Accessibility for the launching terminal/app in macOS System Settings, then restart it."),
        ])
    except ImportError:
        checks.append(Check("desktop_permissions", False, "Desktop permission checks require the SDK desktop dependencies; run uv sync."))
    return checks


def checks_payload(checks: list[Check]) -> dict:
    return {"ready": all(check.ready for check in checks), "checks": [asdict(check) for check in checks]}
