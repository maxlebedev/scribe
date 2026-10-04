from datetime import date

from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import ModalScreen, Screen
from textual.widgets import Static

from app.config import Config
from app.keybinds import DEFAULTS
from app.outline import BlockEditor, Mode, Outline
from app.pages import journal_name
from app.store import load_page, save_page


class ModeLine(Horizontal):
    """Bottom line: the current mode's name, the rest of the line colored by mode."""

    DEFAULT_CSS = """
    ModeLine { dock: bottom; height: 1; background: $panel; }
    ModeLine > #mode { width: auto; padding: 0 1; text-style: bold; color: $text; background: $primary; }
    ModeLine.-insert { background: $warning 25%; }
    ModeLine.-insert > #mode { background: $warning; }
    """

    def compose(self) -> ComposeResult:
        yield Static(Mode.EDIT.upper(), id="mode")

    def show(self, mode: Mode) -> None:
        self.query_one("#mode", Static).update(mode.upper())
        self.set_class(mode is Mode.INSERT, "-insert")


class KeysScreen(ModalScreen, inherit_bindings=False):
    """Pop-up listing every key binding, as currently mapped, by mode."""

    DEFAULT_CSS = """
    KeysScreen { align: center middle; }
    KeysScreen > Static {
        width: auto; height: auto; max-height: 90%; padding: 0 1;
        border: round $primary; border-title-color: $text; background: $surface;
    }
    """
    BINDINGS = [
        Binding(DEFAULTS["to_edit_mode"], "dismiss", "Close", id="to_edit_mode"),
    ]

    def __init__(self, sections: list[tuple[str, list[tuple[str, str]]]]) -> None:
        super().__init__()
        self.sections = sections  # (heading, [(keys, description)])

    def compose(self) -> ComposeResult:
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold", justify="right")
        table.add_column()
        for i, (heading, rows) in enumerate(self.sections):
            if i:
                table.add_row()
            table.add_row("", Text(heading, style="bold underline"))
            for keys, description in rows:
                table.add_row(keys, description)
        box = Static(table)
        box.border_title = "Keys"
        yield box


class MainScreen(Screen, inherit_bindings=False):
    """The default screen without Textual's tab/shift+tab/ctrl+c bindings."""


class ScribeApp(App, inherit_bindings=False):
    # No ctrl+q/ctrl+c/ctrl+p from Textual: every key comes from the keymap.
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding(DEFAULTS["help"], "help", "Show keys", id="help"),
        Binding(DEFAULTS["quit"], "quit", "Quit", id="quit"),
    ]

    def __init__(
        self, config: Config, keymap: dict[str, str] | None = None, today: date | None = None
    ) -> None:
        super().__init__()
        self.config = config
        self.keymap = {**DEFAULTS, **(keymap or {})}
        self.set_keymap(self.keymap)
        self.page = load_page(config.notes_dir, journal_name(today or date.today()))

    def compose(self) -> ComposeResult:
        yield Static(Text(self.page.name, style="bold"), id="title")
        yield Outline(self.page, id="outline")
        yield ModeLine()

    def get_default_screen(self) -> Screen:
        return MainScreen(id="_default")

    def action_help(self) -> None:
        def rows(bindings: list[Binding]) -> list[tuple[str, str]]:
            return [(self._keys_display(b), b.description) for b in bindings]

        self.push_screen(KeysScreen([
            ("Edit mode", rows(Outline.BINDINGS + self.BINDINGS)),
            ("Insert mode", rows(BlockEditor.BINDINGS)),
        ]))

    def _keys_display(self, binding: Binding) -> str:
        keys = self.keymap.get(binding.id, binding.key).split(",")
        return " / ".join(self.get_key_display(Binding(key.strip(), "")) for key in keys)

    def on_outline_mode_changed(self, event: Outline.ModeChanged) -> None:
        self.query_one(ModeLine).show(event.mode)

    def on_outline_changed(self, event: Outline.Changed) -> None:
        try:
            save_page(self.config.notes_dir, self.page)
        except OSError as e:
            self.notify(f"Not saved: {e}", severity="error", timeout=10)
