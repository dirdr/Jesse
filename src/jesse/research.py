"""Research notes: Markdown files describing the researcher's background and usual tools."""
from dataclasses import dataclass
import os
from pathlib import Path

BUDGET_SECONDS = 600
MAX_STEPS = 150
MAX_TRIALS = 12
SEARCH_URL = "https://duckduckgo.com/"
MAX_NOTE_CHARS = 20_000


@dataclass(frozen=True)
class Note:
    id: str
    title: str
    text: str

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title}


def default_root() -> Path:
    return Path(os.environ.get("JESSE_RESEARCH_DIR") or "research")


def load_note(path: Path) -> Note:
    text = path.read_text(encoding="utf-8").strip()
    if len(text) > MAX_NOTE_CHARS:
        raise ValueError(f"{path}: keep each note under {MAX_NOTE_CHARS} characters")
    heading = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), None)
    return Note(path.stem, heading or path.stem.replace("-", " ").capitalize(), text)


def load_notes(root: Path | None = None) -> tuple[Note, ...]:
    root = root or default_root()
    if not root.is_dir():
        return ()
    return tuple(load_note(path) for path in sorted(root.glob("*.md")) if not path.name.startswith(("_", ".")))


def brief(notes: tuple[Note, ...]) -> str:
    if not notes:
        return "The researcher has not written any research notes yet."
    return "\n\n---\n\n".join(note.text for note in notes)
