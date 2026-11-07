"""Synthetic research contexts for tests; never presented as experiment findings."""
from pathlib import Path

from jesse.contexts import ResearchContext, Surface


def synthetic_context(context_id: str = "synthetic-lab", surfaces=("web", "desktop"), **overrides) -> ResearchContext:
    declared = {"web": Surface("web", start_url="https://example.test/lab"), "desktop": Surface("desktop")}
    values = dict(
        id=context_id, title="Synthetic lab", application="Example", activity="Synthetic activity",
        questions=("Compare two synthetic readings.",), surfaces={name: declared[name] for name in surfaces},
        protocol="# Synthetic protocol\n", folder=Path("."), unsupported=("Anything else.",),
        assumptions=("Synthetic fixture",), max_trials=2,
    )
    values.update(overrides)
    return ResearchContext(**values)


CATALOGUE = (synthetic_context(),)


def write_context(root: Path, context_id: str = "demo-lab", toml: str | None = None, tools: str | None = None) -> Path:
    folder = root / context_id
    folder.mkdir(parents=True)
    (folder / "context.toml").write_text(toml or f'''id = "{context_id}"
title = "Demo lab"
application = "Example"
questions = ["Does the synthetic reading change?"]

[surfaces.web]
start_url = "https://example.test/lab"

[surfaces.desktop]
''', encoding="utf-8")
    (folder / "protocol.md").write_text("# Demo protocol\n", encoding="utf-8")
    if tools is not None:
        (folder / "tools.py").write_text(tools, encoding="utf-8")
    return folder
