from datetime import date

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Static

from app.config import Config
from app.markdown import serialize
from app.pages import journal_name
from app.store import load_page


class ScribeApp(App):
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, config: Config, today: date | None = None) -> None:
        super().__init__()
        self.config = config
        self.page = load_page(config.notes_dir, journal_name(today or date.today()))

    def compose(self) -> ComposeResult:
        yield Static(Text(self.page.name, style="bold"), id="title")
        with VerticalScroll():
            # Raw markdown until the outline widget lands (TODO phase 3, item 15).
            # Text, not a str: a str would be parsed as markup and eat `[[links]]`.
            yield Static(Text(serialize(self.page) or "(empty page)"), id="body")
        yield Footer()
