"""Notes directory <-> pages."""

import os
import tempfile
from pathlib import Path

from app.markdown import parse, serialize
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


def save_page(notes_dir: Path, page: Page) -> None:
    """Write the page atomically: a temp file in the same directory, renamed over the old one.

    Readers (and Syncthing) see either the old file or the new one, never a partial write.
    """
    path = page_path(notes_dir, page.name)
    fd, tmp = tempfile.mkstemp(dir=notes_dir, prefix=".scribe-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(serialize(page))
            f.flush()
            os.fsync(f.fileno())
        # mkstemp creates the file 0600; keep the old file's mode, or the umask default.
        try:
            mode = path.stat().st_mode & 0o777
        except FileNotFoundError:
            umask = os.umask(0)
            os.umask(umask)
            mode = 0o666 & ~umask
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
