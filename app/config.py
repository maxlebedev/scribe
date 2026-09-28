"""Settings resolution: CLI argument > config file > default."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_NOTES_DIR = Path("~/notes")


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or "~/.config"
    return Path(base).expanduser() / "scribe" / "config.toml"


@dataclass(frozen=True)
class Config:
    notes_dir: Path


def load_config(notes_dir: str | Path | None = None, path: Path | None = None) -> Config:
    """Resolve settings and ensure the notes directory exists.

    `notes_dir` (from the CLI) wins over the config file, which wins over the default.
    """
    path = path or config_path()
    file_settings = {}
    if path.is_file():
        with path.open("rb") as f:
            file_settings = tomllib.load(f)

    chosen = notes_dir or file_settings.get("notes_dir") or DEFAULT_NOTES_DIR
    resolved = Path(chosen).expanduser().resolve()
    if resolved.exists() and not resolved.is_dir():
        raise NotADirectoryError(f"notes_dir is not a directory: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return Config(notes_dir=resolved)
