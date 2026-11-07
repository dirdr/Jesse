"""NetLogo investigation protocol; independent of provider SDKs."""
from importlib.resources import files
import json

WEB_MODEL_URL = "https://www.netlogoweb.org/assets/modelslib/Sample%20Models/Chemistry%20%26%20Physics/Chemical%20Reactions/Enzyme%20Kinetics.nlogox"
WEB_LAUNCH_URL = "https://www.netlogoweb.org/launch#" + WEB_MODEL_URL


def build_prompt(surface: str = "desktop", application: str | None = None, question: str | None = None) -> str:
    if surface == "web":
        launch = f"Operate NetLogo Web only through the visible browser UI at {WEB_LAUNCH_URL}. Confirm Enzyme Kinetics has loaded."
    elif surface == "desktop":
        launch = "Operate NetLogo Desktop only through screenshots, mouse and keyboard."
        if application:
            launch += f" Installed application: {application}."
    else:
        raise ValueError("Unsupported NetLogo surface")
    if question:
        launch += "\nResearcher question (context only; execute the bounded protocol below): " + json.dumps(question)
    return "\n\n".join(
    (
        launch,
        files("jesse").joinpath("instructions.md").read_text(encoding="utf-8"),
        files(__package__).joinpath("measurement.md").read_text(encoding="utf-8"),
        files(__package__).joinpath("protocol.md").read_text(encoding="utf-8"),
    )
    )


PROMPT = build_prompt()

