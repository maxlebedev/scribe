from textual.app import App, ComposeResult
from textual.widgets import Footer, Static

from app.config import Config


class ScribeApp(App):
    # Placeholder shell until the outline view lands (TODO phase 3).
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        yield Static(f"Notes: {self.config.notes_dir}")
        yield Footer()
