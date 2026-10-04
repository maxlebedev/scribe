"""Read-only outline of a page's blocks with a block cursor."""

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static

from app.keybinds import DEFAULTS
from app.model import Block, Page

INDENT = 2  # columns per nesting level


class BlockView(Horizontal):
    """One block: bullet plus content, wrapped lines hang under the content."""

    DEFAULT_CSS = """
    BlockView { height: auto; }
    BlockView > .bullet { width: 2; }
    BlockView > .content { width: 1fr; }
    BlockView.-cursor { background: $boost; }
    """

    def __init__(self, block: Block, depth: int) -> None:
        super().__init__()
        self.block = block
        self.styles.padding = (0, 0, 0, depth * INDENT)

    def compose(self) -> ComposeResult:
        yield Static("•", classes="bullet")
        # Text, not a str: a str would be parsed as markup and eat `[[links]]`.
        yield Static(Text(self.block.content), classes="content")


class Outline(VerticalScroll):
    BINDINGS = [
        Binding(DEFAULTS["cursor_up"], "cursor_up", "Up", id="cursor_up"),
        Binding(DEFAULTS["cursor_down"], "cursor_down", "Down", id="cursor_down"),
    ]

    def __init__(self, page: Page, **kwargs) -> None:
        super().__init__(**kwargs)
        self.page = page
        self.cursor = 0  # index into the page's blocks in document order

    def compose(self) -> ComposeResult:
        for block, depth in self.page.walk():
            yield BlockView(block, depth)
        if not self.page.blocks:
            yield Static("(empty page)", classes="empty")

    def on_mount(self) -> None:
        self._move_to(0)

    @property
    def cursor_block(self) -> Block | None:
        views = self.query(BlockView)
        return views[self.cursor].block if views else None

    def action_cursor_down(self) -> None:
        self._move_to(self.cursor + 1)

    def action_cursor_up(self) -> None:
        self._move_to(self.cursor - 1)

    def _move_to(self, index: int) -> None:
        views = self.query(BlockView)
        if not views:
            return
        views[self.cursor].remove_class("-cursor")
        self.cursor = max(0, min(index, len(views) - 1))
        views[self.cursor].add_class("-cursor")
        views[self.cursor].scroll_visible()
