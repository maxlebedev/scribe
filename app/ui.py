from datetime import date

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Static

from app.config import Config
from app.keybinds import DEFAULTS
from app.outline import Mode, Outline
from app.pages import journal_name
from app.store import load_page, save_page


class ModeLine(Horizontal):
    """Bottom line: the current mode's name, then the footer's key hints, colored by mode."""

    DEFAULT_CSS = """
    ModeLine { dock: bottom; height: 1; }
    ModeLine > #mode { width: auto; padding: 0 1; text-style: bold; color: $text; background: $primary; }
    ModeLine > Footer { dock: none; width: 1fr; }
    ModeLine.-edit > #mode { background: $warning; }
    ModeLine.-edit > Footer { background: $warning 25%; }
    """

    def compose(self) -> ComposeResult:
        yield Static(Mode.VIEW.upper(), id="mode")
        yield Footer()

    def show(self, mode: Mode) -> None:
        self.query_one("#mode", Static).update(mode.upper())
        self.set_class(mode is Mode.EDIT, "-edit")


class ScribeApp(App):
    BINDINGS = [Binding(DEFAULTS["quit"], "quit", "Quit", id="quit")]

    def __init__(
        self, config: Config, keymap: dict[str, str] | None = None, today: date | None = None
    ) -> None:
        super().__init__()
        self.config = config
        if keymap:
            self.set_keymap(keymap)
        self.page = load_page(config.notes_dir, journal_name(today or date.today()))

    def compose(self) -> ComposeResult:
        yield Static(Text(self.page.name, style="bold"), id="title")
        yield Outline(self.page, id="outline")
        yield ModeLine()

    def on_outline_mode_changed(self, event: Outline.ModeChanged) -> None:
        self.query_one(ModeLine).show(event.mode)

    def on_outline_changed(self, event: Outline.Changed) -> None:
        try:
            save_page(self.config.notes_dir, self.page)
        except OSError as e:
            self.notify(f"Not saved: {e}", severity="error", timeout=10)
