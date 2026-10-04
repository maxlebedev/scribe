from datetime import date

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Static

from app.config import Config
from app.keybinds import DEFAULTS
from app.outline import Outline
from app.pages import journal_name
from app.store import load_page


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
        yield Footer()
