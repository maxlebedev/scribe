import pytest

from app.keybinds import DEFAULTS, load_keybinds


def test_missing_file_written_with_defaults(tmp_path):
    path = tmp_path / "scribe" / "keybinds.yaml"
    assert load_keybinds(path) == DEFAULTS
    assert load_keybinds(path) == DEFAULTS  # the written file reads back the same


def test_file_overrides_defaults(tmp_path):
    path = tmp_path / "keybinds.yaml"
    path.write_text("cursor_down: l\ncursor_up: [k, up]\n")
    assert load_keybinds(path) == {**DEFAULTS, "cursor_down": "l", "cursor_up": "k,up"}


def test_empty_file_means_defaults(tmp_path):
    path = tmp_path / "keybinds.yaml"
    path.write_text("# nothing\n")
    assert load_keybinds(path) == DEFAULTS


@pytest.mark.parametrize(
    "text",
    [
        "cursr_down: j\n",  # typo'd action
        "quit: off\n",  # YAML reads unquoted off as False
        "quit: 1\n",
        "quit: []\n",
        "- q\n",  # not a mapping
        "quit: [q\n",  # invalid YAML
    ],
)
def test_bad_file_rejected(tmp_path, text):
    path = tmp_path / "keybinds.yaml"
    path.write_text(text)
    with pytest.raises(ValueError):
        load_keybinds(path)
