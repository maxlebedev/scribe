"""Outline of a page's blocks: a block cursor in view mode, a TextArea in edit mode.

Edits change the in-memory block only; writing to disk is TODO phase 6.
"""

from enum import StrEnum

from rich.console import Group
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.message import Message
from textual.widgets import Static, TextArea

from app.keybinds import DEFAULTS
from app.model import Block, Page
from app.render import render_block, render_page_properties

INDENT = 2  # columns per nesting level


class Mode(StrEnum):
    VIEW = "view"
    EDIT = "edit"


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
        self.depth = depth
        self.styles.padding = (0, 0, 0, depth * INDENT)

    def compose(self) -> ComposeResult:
        yield Static("•", classes="bullet")
        yield Static(Group(*render_block(self.block)), classes="content")

    async def start_edit(self, at_start: bool = False) -> None:
        self.query_one(".content").display = False
        editor = BlockEditor(self.block.content)
        await self.mount(editor)
        editor.move_cursor((0, 0) if at_start else editor.document.end)
        editor.focus()

    async def finish_edit(self, text: str) -> bool:
        """End the edit; returns whether the block's text changed."""
        # Trailing blank lines would be dropped on the next parse anyway.
        old, self.block.content = self.block.content, text.rstrip("\n")
        await self.query_one(BlockEditor).remove()
        content = self.query_one(".content", Static)
        content.update(Group(*render_block(self.block)))
        content.display = True
        return self.block.content != old


class BlockEditor(TextArea):
    """Edits one block's raw text. The commit key ends the edit; the split key ends it and
    moves the text after the cursor into a new block."""

    DEFAULT_CSS = """
    BlockEditor { width: 1fr; height: auto; padding: 0; }
    """
    BINDINGS = [
        # priority: TextArea would otherwise use escape to move focus away.
        Binding(DEFAULTS["commit_edit"], "commit", "Done", id="commit_edit", priority=True),
        # priority: TextArea would otherwise insert a newline for enter.
        Binding(DEFAULTS["split_block"], "split", "New block", id="split_block", priority=True),
        Binding(DEFAULTS["insert_newline"], "newline", "Newline", id="insert_newline", priority=True),
    ]

    class Committed(Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    class Split(Message):
        def __init__(self, before: str, after: str) -> None:
            super().__init__()
            self.before = before
            self.after = after

    def __init__(self, text: str) -> None:
        super().__init__(text, soft_wrap=True, tab_behavior="indent", compact=True)

    def action_commit(self) -> None:
        self.post_message(self.Committed(self.text))

    def action_split(self) -> None:
        cursor = self.cursor_location
        before = self.get_text_range((0, 0), cursor)
        after = self.get_text_range(cursor, self.document.end)
        self.post_message(self.Split(before, after))

    def action_newline(self) -> None:
        self.insert("\n")


class Outline(VerticalScroll):
    class Changed(Message):
        """The page's blocks changed and should be saved."""

    class ModeChanged(Message):
        def __init__(self, mode: Mode) -> None:
            super().__init__()
            self.mode = mode

    BINDINGS = [
        Binding(DEFAULTS["cursor_up"], "cursor_up", "Up", id="cursor_up"),
        Binding(DEFAULTS["cursor_down"], "cursor_down", "Down", id="cursor_down"),
        Binding(DEFAULTS["edit_block_start"], "edit_block(True)", "Edit at start", id="edit_block_start"),
        Binding(DEFAULTS["edit_block_end"], "edit_block", "Edit at end", id="edit_block_end"),
    ]

    def __init__(self, page: Page, **kwargs) -> None:
        super().__init__(**kwargs)
        self.page = page
        self.cursor = 0  # index into the page's blocks in document order
        self.editing: BlockView | None = None

    def compose(self) -> ComposeResult:
        if self.page.property_lines:
            yield Static(render_page_properties(self.page.property_lines), classes="page-properties")
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

    @property
    def mode(self) -> Mode:
        return Mode.EDIT if self.editing else Mode.VIEW

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        # View-mode actions are off (and hidden from the footer) in edit mode.
        return not (self.mode is Mode.EDIT and action in {"cursor_up", "cursor_down", "edit_block"})

    def _mode_changed(self) -> None:
        self.refresh_bindings()
        self.post_message(self.ModeChanged(self.mode))

    async def action_edit_block(self, at_start: bool = False) -> None:
        if self.editing:
            return
        if not self.page.blocks:  # empty page: editing starts its first block
            block = Block()
            self.page.blocks.append(block)
            await self.query(".empty").remove()
            await self.mount(BlockView(block, 0))
            self._move_to(0)
        self.editing = self.query(BlockView)[self.cursor]
        self._mode_changed()
        await self.editing.start_edit(at_start)

    async def on_block_editor_committed(self, event: BlockEditor.Committed) -> None:
        event.stop()
        view, self.editing = self.editing, None
        self._mode_changed()
        if await view.finish_edit(event.text):
            self.post_message(self.Changed())
        self.focus()

    async def on_block_editor_split(self, event: BlockEditor.Split) -> None:
        """Commit the text before the cursor; the rest becomes a new block, edited from its start.

        The new block goes right below the current one on screen: its first child if it has
        children, else its next sibling. Stays in edit mode throughout.
        """
        event.stop()
        view = self.editing
        await view.finish_edit(event.before)
        new = Block(content=event.after.lstrip("\n"))
        if view.block.children:
            view.block.add_child(new, 0)
            depth = view.depth + 1
        else:
            self.page.insert_after(view.block, new)
            depth = view.depth
        self.editing = BlockView(new, depth)
        await self.mount(self.editing, after=view)
        self._move_to(self.cursor + 1)
        self.post_message(self.Changed())
        await self.editing.start_edit(at_start=True)

    def _move_to(self, index: int) -> None:
        views = self.query(BlockView)
        if not views:
            return
        views[self.cursor].remove_class("-cursor")
        self.cursor = max(0, min(index, len(views) - 1))
        views[self.cursor].add_class("-cursor")
        views[self.cursor].scroll_visible()
