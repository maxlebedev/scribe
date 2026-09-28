from pathlib import Path

import pytest

from app.config import load_config


@pytest.fixture
def cfg_file(tmp_path: Path) -> Path:
    return tmp_path / "config.toml"


def test_cli_arg_wins_over_config_file(tmp_path, cfg_file):
    cfg_file.write_text(f'notes_dir = "{tmp_path / "from_file"}"\n')
    config = load_config(tmp_path / "from_cli", path=cfg_file)
    assert config.notes_dir == tmp_path / "from_cli"


def test_config_file_used_when_no_cli_arg(tmp_path, cfg_file):
    cfg_file.write_text(f'notes_dir = "{tmp_path / "from_file"}"\n')
    assert load_config(path=cfg_file).notes_dir == tmp_path / "from_file"


def test_default_when_no_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config = load_config(path=tmp_path / "missing.toml")
    assert config.notes_dir == tmp_path / "notes"


def test_creates_missing_notes_dir(tmp_path, cfg_file):
    target = tmp_path / "a" / "b"
    load_config(target, path=cfg_file)
    assert target.is_dir()


def test_expands_tilde(tmp_path, cfg_file, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg_file.write_text('notes_dir = "~/journal"\n')
    assert load_config(path=cfg_file).notes_dir == tmp_path / "journal"


def test_rejects_file_as_notes_dir(tmp_path, cfg_file):
    not_a_dir = tmp_path / "file.md"
    not_a_dir.write_text("")
    with pytest.raises(NotADirectoryError):
        load_config(not_a_dir, path=cfg_file)
