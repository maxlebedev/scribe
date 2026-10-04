"""Notes directory <-> pages."""

from pathlib import Path

from app.markdown import parse
from app.model import Page
from app.pages import filename_for


def page_path(notes_dir: Path, name: str) -> Path:
    return notes_dir / filename_for(name)


def load_page(notes_dir: Path, name: str) -> Page:
    """Parse the page's file. A missing page is created on disk as an empty file."""
    path = page_path(notes_dir, name)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        path.touch(exist_ok=True)
        return Page(name=name)
    return parse(text, name=name)
