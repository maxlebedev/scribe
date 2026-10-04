from pathlib import Path

import pytest
import yaml

from app.keybinds import DEFAULTS, load_keybinds

KEYBINDS = Path(__file__).parent / "fixtures" / "keybinds.yaml"


@pytest.fixture
def keymap() -> dict[str, str]:
    """Keybindings from tests/fixtures/keybinds.yaml: down n, up p, quit x."""
    assert yaml.safe_load(KEYBINDS.read_text()).keys() == DEFAULTS.keys(), (
        f"{KEYBINDS} must bind every action, or tests fall back to the defaults"
    )
    return load_keybinds(KEYBINDS)
