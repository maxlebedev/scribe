"""Outline of a page's blocks: a block cursor in view mode, a TextArea in edit mode.

Edits update the in-memory page and post `Outline.Changed`; the app saves.
The cursor block is joined to its parent by a guide: a line down from the parent's bullet
that turns into the cursor block's bullet.
"""

from enum import StrEnum

from rich.console import Group
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static, TextArea

from app.keybinds import DEFAULTS
from app.model import Block, Page
from app.render import render_block, render_page_properties

INDENT = 2  # columns per nesting level


# The page's blocks as (content, depth) rows, and the cursor index.
Snapshot = tuple[list[tuple[str, int]], int]


class Mode(StrEnum):
    VIEW = "view"
    EDIT = "edit"


class Gutter(Widget):
    """The indent left of a block's bullet, as tall as the block. Draws the guide passing
    through it: `│` in column `guide`, or `╰─` on the first row when `corner` is set."""

    COMPONENT_CLASSES = {"gutter--guide"}
    DEFAULT_CSS = """
    Gutter { height: 100%; }
    Gutter > .gutter--guide { color: $primary; }
    """
    guide: reactive[int | None] = reactive(None)
    corner = reactive(False)

    def __init__(self, depth: int) -> None:
        super().__init__()
        self.styles.width = depth * INDENT

    def render(self) -> Text:
        width, height = self.size
        style = self.get_component_rich_style("gutter--guide")
        rows = []
        for y in range(height):
            row = Text(" " * width)
            if self.guide is not None:
                if self.corner and y == 0:
                    row = Text(" " * self.guide) + Text("╰" + "─" * (width - self.guide - 1), style)
                elif not self.corner:
                    row = Text(" " * self.guide) + Text("│", style) + Text(" " * (width - self.guide - 1))
            rows.append(row)
        return Text("\n").join(rows)


class Bullet(Widget):
    """The block's bullet, as tall as the block. With `stem`, the guide continues down from it."""

    COMPONENT_CLASSES = {"bullet--guide"}
    DEFAULT_CSS = """
    Bullet { width: 2; height: 100%; }
    Bullet > .bullet--guide { color: $primary; }
    """
    lit = reactive(False)  # on the guide: colored like it
    stem = reactive(False)

    def render(self) -> Text:
        style = self.get_component_rich_style("bullet--guide")
        rows = [Text("•", style if self.lit else "")]
        rows += [Text("│" if self.stem else " ", style) for _ in range(self.size.height - 1)]
        return Text("\n").join(rows)


class BlockView(Horizontal):
    """One block: indent, bullet, content. Wrapped lines hang under the content."""

    DEFAULT_CSS = """
    BlockView { height: auto; }
    BlockView > .content { width: 1fr; }
    BlockView.-cursor { background: $boost; }
    """

    def __init__(self, block: Block, depth: int) -> None:
        super().__init__()
        self.block = block
        self.depth = depth
        self.indent_gutter = Gutter(depth)
        self.bullet = Bullet()

    def compose(self) -> ComposeResult:
        yield self.indent_gutter
        yield self.bullet
        yield Static(Group(*render_block(self.block)), classes="content")

    async def start_edit(self, at_start: bool = False) -> None:
        self.query_one(".content").display = False
        editor = BlockEditor(self.block.content)
        await self.mount(editor)
        editor.move_cursor((0, 0) if at_start else editor.document.end)
        editor.focus()

    async def finish_edit(self, text: str) -> None:
        # Trailing blank lines would be dropped on the next parse anyway.
        self.block.content = text.rstrip("\n")
        await self.query_one(BlockEditor).remove()
        content = self.query_one(".content", Static)
        content.update(Group(*render_block(self.block)))
        content.display = True


class BlockEditor(TextArea):
    """Edits one block's raw text. The commit key ends the edit; the split key ends it and
    moves the text after the cursor into a new block."""

    DEFAULT_CSS = """
    BlockEditor { width: 1fr; height: auto; padding: 0; }
    """
    BINDINGS = [
        # priority: TextArea would otherwise use escape to move focus away.
        Binding(DEFAULTS["to_view_mode"], "commit", "Done", id="to_view_mode", priority=True),
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


class Outline(VerticalScroll, inherit_bindings=False):  # no scroll keys
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
        Binding(DEFAULTS["new_block_below"], "new_block(True)", "New block below", id="new_block_below"),
        Binding(DEFAULTS["new_block_above"], "new_block(False)", "New block above", id="new_block_above"),
        Binding(DEFAULTS["delete_block"], "delete_block", "Delete", id="delete_block"),
        Binding(DEFAULTS["indent_block"], "indent_block", "Indent", id="indent_block"),
        Binding(DEFAULTS["outdent_block"], "outdent_block", "Outdent", id="outdent_block"),
        Binding(DEFAULTS["undo"], "undo", "Undo", id="undo"),
        Binding(DEFAULTS["redo"], "redo", "Redo", id="redo"),
    ]

    def __init__(self, page: Page, **kwargs) -> None:
        super().__init__(**kwargs)
        self.page = page
        self.cursor = 0  # index into the page's blocks in document order
        self.editing: BlockView | None = None
        # Undo/redo steps: (before, after) snapshots. An edit session, from entering edit
        # mode to leaving it (splits included), is one step.
        self.undo_stack: list[tuple[Snapshot, Snapshot]] = []
        self.redo_stack: list[tuple[Snapshot, Snapshot]] = []
        self._before_edit: Snapshot | None = None

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
        return self.mode is Mode.VIEW

    def _mode_changed(self) -> None:
        self.refresh_bindings()
        self.post_message(self.ModeChanged(self.mode))

    async def action_edit_block(self, at_start: bool = False) -> None:
        if not self.page.blocks:  # empty page: editing starts its first block
            await self.action_new_block()
            return
        await self._start_edit(at_start, self._snapshot())

    async def action_new_block(self, below: bool = True) -> None:
        """Add an empty block right below the cursor block on screen (its first child if it
        has children, else its next sibling) or above it (its previous sibling), and edit it.
        Adding and editing are one undo step."""
        before = self._snapshot()
        new, current = Block(), self.cursor_block
        if current is None:
            self.page.blocks.append(new)
        elif below and current.children:
            current.add_child(new, 0)
        elif below:
            self.page.insert_after(current, new)
        else:
            self.page.insert_before(current, new)
        await self._redraw(new)
        await self._start_edit(True, before)

    async def _start_edit(self, at_start: bool, before: Snapshot) -> None:
        self._before_edit = before
        self.editing = self.query(BlockView)[self.cursor]
        self._mode_changed()
        await self.editing.start_edit(at_start)

    async def on_block_editor_committed(self, event: BlockEditor.Committed) -> None:
        event.stop()
        view, self.editing = self.editing, None
        self._mode_changed()
        await view.finish_edit(event.text)
        if self._before_edit[0] != self.page.outline():
            self.post_message(self.Changed())
            self._record(self._before_edit)
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

    async def action_delete_block(self) -> None:
        if block := self.cursor_block:

            def delete() -> bool:
                self.page.remove(block)
                return True

            await self._change(delete, self.cursor)  # the next block takes its place

    async def action_indent_block(self) -> None:
        if block := self.cursor_block:
            await self._change(lambda: self.page.indent_block(block), block)

    async def action_outdent_block(self) -> None:
        if block := self.cursor_block:
            await self._change(lambda: self.page.outdent_block(block), block)

    async def action_undo(self) -> None:
        if self.undo_stack:
            step = self.undo_stack.pop()
            self.redo_stack.append(step)
            await self._restore(step[0])

    async def action_redo(self) -> None:
        if self.redo_stack:
            step = self.redo_stack.pop()
            self.undo_stack.append(step)
            await self._restore(step[1])

    def _snapshot(self) -> Snapshot:
        return self.page.outline(), self.cursor

    def _record(self, before: Snapshot | None) -> None:
        """Push an undo step from `before` to now, if the page has changed since."""
        if before is not None and before[0] != self.page.outline():
            self.undo_stack.append((before, self._snapshot()))
            self.redo_stack.clear()

    async def _change(self, apply, cursor: Block | int) -> None:
        """Apply a structural change (`apply()` returns whether anything changed), record it
        for undo, save, and redraw with the cursor on `cursor` (a block, or an index)."""
        before = self._snapshot()
        if not apply():
            return
        self.post_message(self.Changed())
        await self._redraw(cursor)
        self._record(before)

    async def _restore(self, snapshot: Snapshot) -> None:
        rows, cursor = snapshot
        self.page.set_outline(rows)
        self.post_message(self.Changed())
        await self._redraw(cursor)

    async def _redraw(self, cursor: Block | int) -> None:
        await self.recompose()
        if isinstance(cursor, Block):
            cursor = next(i for i, (b, _) in enumerate(self.page.walk()) if b is cursor)
        self._move_to(cursor)

    def _move_to(self, index: int) -> None:
        views = self.query(BlockView)
        if not views:
            return
        if self.cursor < len(views):
            views[self.cursor].remove_class("-cursor")
        self.cursor = max(0, min(index, len(views) - 1))
        views[self.cursor].add_class("-cursor")
        views[self.cursor].scroll_visible()
        self._draw_guide(list(views))

    def _draw_guide(self, views: list[BlockView]) -> None:
        """Trace the cursor block's ancestry up to its top-level block. Each ancestor's bullet
        stems down, every block in between carries the line in its gutter, and the next block
        on the path turns it in. Segments never share a row, so a gutter carries one line."""
        for view in views:
            view.indent_gutter.guide, view.indent_gutter.corner = None, False
            view.bullet.lit = view.bullet.stem = False
        index = {id(v.block): i for i, v in enumerate(views)}
        path = [self.cursor]  # view indexes from the cursor block up to its top-level block
        while (parent := views[path[-1]].block.parent) is not None:
            path.append(index[id(parent)])
        views[self.cursor].bullet.lit = True
        for child, top in zip(path, path[1:]):
            views[top].bullet.lit = views[top].bullet.stem = True
            column = views[top].depth * INDENT
            for view in views[top + 1 : child + 1]:
                view.indent_gutter.guide = column
            views[child].indent_gutter.corner = True
