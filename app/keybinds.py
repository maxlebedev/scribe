"""User-editable keybindings: `keybinds.yaml` next to `config.toml`.

Each binding has an id (the YAML key); the file maps ids to keys. Ids missing from the
file keep their defaults. Textual applies the result via `App.set_keymap`.
"""

from pathlib import Path

import yaml

from app.config import config_path

DEFAULTS = {
    "cursor_down": "j",
    "cursor_up": "k",
    "edit_block_start": "a",
    "edit_block_end": "e",
    "new_block_below": "o",
    "new_block_above": "O",
    "delete_block": "d",
    "indent_block": ">",
    "outdent_block": "<",
    "undo": "u",
    "redo": "r",
    "to_view_mode": "escape",  # leaves edit mode, closes pop-ups
    "split_block": "enter",
    # shift+enter only reaches us in terminals that report it (not Vim's :terminal).
    "insert_newline": "shift+enter,ctrl+j",
    "help": "?",
    "quit": "q",
}

_HEADER = """\
# Scribe keybindings: action: key, or action: [key, key, ...]
# Key names are Textual's: a, A, up, tab, shift+tab, ctrl+o, ...
# Quote keys YAML would otherwise read as booleans or numbers: "on", "off", "yes", "no", "1".
"""


def keybinds_path() -> Path:
    return config_path().parent / "keybinds.yaml"


def load_keybinds(path: Path | None = None) -> dict[str, str]:
    """Defaults overridden by the file; writes the defaults out if the file is missing."""
    path = path or keybinds_path()
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_HEADER + yaml.safe_dump(DEFAULTS, sort_keys=False))
        return dict(DEFAULTS)

    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"{path}: {e}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping of action: key")

    keymap = dict(DEFAULTS)
    for action, keys in data.items():
        if action not in DEFAULTS:
            raise ValueError(
                f"{path}: unknown action {action!r} (known: {', '.join(DEFAULTS)})"
            )
        keys = keys if isinstance(keys, list) else [keys]
        if not keys or not all(isinstance(k, str) and k for k in keys):
            raise ValueError(
                f"{path}: {action}: keys must be non-empty strings (quote them)"
            )
        keymap[action] = ",".join(keys)
    return keymap
