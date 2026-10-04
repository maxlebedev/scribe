import asyncio

from textual.app import App
from textual.widgets import Static

from app.markdown import parse
from app.render import MARKER_STYLES
from app.outline import BlockEditor, BlockView, Outline

TEXT = "- a\n\t- b\n\t  more\n\t\t- c\n- d\n"


class Host(App):
    def __init__(self, text, keymap):
        super().__init__()
        self.page = parse(text)
        self.set_keymap(keymap)
        self.changes = 0

    def on_outline_changed(self, event):
        self.changes += 1

    def compose(self):
        yield Outline(self.page)


def run(keymap, text, keys=()):
    """Press `keys` (n = down, p = up), then return (block contents, indents, cursor block content, highlighted)."""

    async def go():
        app = Host(text, keymap)
        async with app.run_test() as pilot:
            await pilot.press(*keys)
            outline = app.query_one(Outline)
            views = list(outline.query(BlockView))
            cursor = outline.cursor_block
            return (
                [v.block.content for v in views],
                [v.indent_gutter.styles.width.value for v in views],
                cursor.content if cursor else None,
                [v.block.content for v in views if v.has_class("-cursor")],
            )

    return asyncio.run(go())


def test_renders_one_view_per_block_with_indent(keymap):
    contents, indents, _, _ = run(keymap, TEXT)
    assert contents == ["a", "b\nmore", "c", "d"]
    assert indents == [0, 2, 4, 0]


def test_cursor_starts_on_first_block(keymap):
    assert run(keymap, TEXT)[2] == "a"


def test_cursor_moves_in_document_order(keymap):
    assert run(keymap, TEXT, ["n", "n"])[2] == "c"
    assert run(keymap, TEXT, ["n", "n", "n", "p"])[2] == "c"


def test_cursor_clamps_at_ends(keymap):
    assert run(keymap, TEXT, ["p"])[2] == "a"
    assert run(keymap, TEXT, ["n"] * 10)[2] == "d"


def test_only_cursor_block_highlighted(keymap):
    assert run(keymap, TEXT, ["n"])[3] == ["b\nmore"]


def test_empty_page_has_no_cursor(keymap):
    assert run(keymap, "", ["n", "p"])[2] is None


def test_page_properties_shown_above_blocks(keymap):
    async def go():
        app = Host("title:: Hi\n\n- a\n", keymap)
        async with app.run_test():
            outline = app.query_one(Outline)
            props = outline.query_one(".page-properties", Static)
            return str(props.content), outline.children.index(props), outline.cursor_block.content

    assert asyncio.run(go()) == ("title:: Hi", 0, "a")


# --- Editing (tests/fixtures/keybinds.yaml): s/d edit at start/end, ctrl+g commits,
# ctrl+b splits into a new block, ctrl+l inserts a newline. ---


def keys_for(text):
    return ["space" if c == " " else "ctrl+l" if c == "\n" else c for c in text]


def edit(keymap, text, keys):
    """Press `keys`, then return (page, focused widget type, editor text or None, cursor block)."""

    async def go():
        app = Host(text, keymap)
        async with app.run_test() as pilot:
            await pilot.press(*keys)
            await pilot.pause()
            outline = app.query_one(Outline)
            editors = outline.query(BlockEditor)
            return (
                app.page,
                type(app.focused),
                editors.first().text if editors else None,
                outline.cursor_block,
            )

    return asyncio.run(go())


def test_edit_opens_editor_with_block_text(keymap):
    _, focused, editor_text, _ = edit(keymap, TEXT, ["n", "d"])
    assert focused is BlockEditor and editor_text == "b\nmore"


def test_typing_appends_and_commit_updates_block(keymap):
    page, focused, editor_text, block = edit(keymap, TEXT, ["d", *keys_for(" done"), "ctrl+g"])
    assert block.content == "a done" and page.blocks[0] is block
    assert focused is Outline and editor_text is None


def test_normal_mode_keys_are_text_while_editing(keymap):
    page, _, editor_text, block = edit(keymap, TEXT, ["d", "n", "p", "x"])
    assert editor_text == "anpx" and block is page.blocks[0]  # no move, no quit


def test_newline_key_inserts_newline_while_editing(keymap):
    _, _, _, block = edit(keymap, TEXT, ["d", *keys_for("\nsecond"), "ctrl+g"])
    assert block.content == "a\nsecond"


def test_commit_drops_trailing_blank_lines(keymap):
    _, _, _, block = edit(keymap, TEXT, ["d", "ctrl+l", "ctrl+l", "ctrl+g"])
    assert block.content == "a"


def test_commit_rerenders_block(keymap):
    async def go():
        app = Host(TEXT, keymap)
        async with app.run_test() as pilot:
            await pilot.press("d", "home", *keys_for("TODO "), "ctrl+g")
            await pilot.pause()
            content = app.query(BlockView).first().query_one(".content", Static)
            [text] = content.content.renderables
            return content.display, text

    display, text = asyncio.run(go())
    assert display and text.plain == "TODO a"
    assert ("TODO", MARKER_STYLES["TODO"]) in [(text.plain[s.start : s.end], s.style) for s in text.spans]


def test_edit_on_empty_page_creates_first_block(keymap):
    page, _, _, block = edit(keymap, "", ["d", *keys_for("hello"), "ctrl+g"])
    assert [b.content for b in page.blocks] == ["hello"] and block is page.blocks[0]


def test_only_commit_key_active_while_editing(keymap):
    async def go():
        app = Host(TEXT, keymap)
        async with app.run_test() as pilot:
            await pilot.press("d")
            await pilot.pause()
            return sorted(b.binding.id for b in app.active_bindings.values() if b.enabled and b.binding.id)

    assert asyncio.run(go()) == ["insert_newline", "split_block", "to_view_mode"]


def test_edit_at_start_and_end(keymap):
    _, _, _, block = edit(keymap, TEXT, ["n", "s", *keys_for("X"), "ctrl+g"])
    assert block.content == "Xb\nmore"
    _, _, _, block = edit(keymap, TEXT, ["n", "d", *keys_for("X"), "ctrl+g"])
    assert block.content == "b\nmoreX"


def split(keymap, text, keys):
    """Press `keys`, then return ((content, depth) per view in order, cursor block, focused type)."""

    async def go():
        app = Host(text, keymap)
        async with app.run_test() as pilot:
            await pilot.press(*keys)
            await pilot.pause()
            outline = app.query_one(Outline)
            views = [(v.block.content, v.depth) for v in outline.query(BlockView)]
            return views, outline.cursor_block, type(app.focused), app.page

    return asyncio.run(go())


def test_split_at_end_of_leaf_adds_next_sibling(keymap):
    views, cursor, focused, page = split(keymap, "- a\n- b\n", ["d", "ctrl+b", *keys_for("new")])
    assert focused is BlockEditor and cursor is page.blocks[1]
    assert [(c, d) for c, d in views] == [("a", 0), ("", 0), ("b", 0)]
    _, _, _, page = split(keymap, "- a\n- b\n", ["d", "ctrl+b", *keys_for("new"), "ctrl+g"])
    assert [b.content for b in page.blocks] == ["a", "new", "b"]


def test_split_block_with_children_adds_first_child(keymap):
    views, cursor, _, page = split(keymap, TEXT, ["d", "ctrl+b", *keys_for("x"), "ctrl+g"])
    assert views[:3] == [("a", 0), ("x", 1), ("b\nmore", 1)]
    assert page.blocks[0].children[0] is cursor and cursor.parent is page.blocks[0]


def test_split_in_middle_moves_rest_to_new_block(keymap):
    keys = ["d", *["left"] * 5, "ctrl+b", "ctrl+g"]
    views, cursor, _, _ = split(keymap, "- hello world\n", keys)
    assert views == [("hello ", 0), ("world", 0)] and cursor.content == "world"


def test_split_at_line_end_drops_leading_newline(keymap):
    views, _, _, _ = split(keymap, "- one\n  two\n", ["s", "end", "ctrl+b", "ctrl+g"])
    assert views == [("one", 0), ("two", 0)]


def test_new_block_edited_from_its_start(keymap):
    views, _, _, _ = split(keymap, "- hello world\n", ["d", *["left"] * 5, "ctrl+b", "X", "ctrl+g"])
    assert views == [("hello ", 0), ("Xworld", 0)]


def guide(keymap, text, keys):
    """Press `keys`, then return each view's (gutter guide, corner, bullet lit, bullet stem)."""

    async def go():
        app = Host(text, keymap)
        async with app.run_test() as pilot:
            await pilot.press(*keys)
            views = app.query_one(Outline).query(BlockView)
            return [(v.indent_gutter.guide, v.indent_gutter.corner, v.bullet.lit, v.bullet.stem) for v in views]

    return asyncio.run(go())


def test_guide_joins_cursor_to_parent(keymap):
    # a > [b > c, x], d: cursor on x, so the guide runs from a past b and c.
    text = "- a\n\t- b\n\t\t- c\n\t- x\n- d\n"
    assert guide(keymap, text, ["n", "n", "n"]) == [
        (None, False, True, True),  # a: parent, stems down
        (0, False, False, False),  # b: line passes through
        (0, False, False, False),  # c
        (0, True, True, False),  # x: cursor, line turns in
        (None, False, False, False),  # d
    ]


def test_no_guide_on_top_level_block(keymap):
    text = "- a\n\t- b\n- d\n"
    assert guide(keymap, text, ["n", "n"])[2] == (None, False, True, False)
    assert all(g is None for g, *_ in guide(keymap, text, ["n", "n"]))


# --- Block ops (tests/fixtures/keybinds.yaml): z delete, ] indent, [ outdent, h undo, t redo. ---


def ops(keymap, text, keys):
    """Press `keys`, then return ((content, depth) per view, cursor block content, changes posted)."""

    async def go():
        app = Host(text, keymap)
        async with app.run_test() as pilot:
            await pilot.press(*keys)
            await pilot.pause()
            outline = app.query_one(Outline)
            views = [(v.block.content, v.depth) for v in outline.query(BlockView)]
            assert views == [(b.content, d) for b, d in app.page.walk()]  # screen matches model
            cursor = outline.cursor_block
            return views, cursor.content if cursor else None, app.changes

    return asyncio.run(go())


def test_delete_removes_block_with_children(keymap):
    views, cursor, changes = ops(keymap, TEXT, ["z"])
    assert views == [("d", 0)] and cursor == "d" and changes == 1


def test_delete_last_block_moves_cursor_up(keymap):
    views, cursor, _ = ops(keymap, "- a\n- b\n", ["n", "z"])
    assert views == [("a", 0)] and cursor == "a"


def test_delete_everything_leaves_empty_page(keymap):
    views, cursor, _ = ops(keymap, "- a\n", ["z", "z"])
    assert views == [] and cursor is None


def test_indent_and_outdent_keep_cursor_on_block(keymap):
    views, cursor, changes = ops(keymap, "- a\n- b\n- c\n", ["n", "]"])
    assert views == [("a", 0), ("b", 1), ("c", 0)] and cursor == "b" and changes == 1
    views, cursor, _ = ops(keymap, "- a\n\t- b\n\t- c\n", ["n", "["])
    assert views == [("a", 0), ("b", 0), ("c", 1)] and cursor == "b"


def test_impossible_indent_changes_nothing(keymap):
    views, _, changes = ops(keymap, "- a\n- b\n", ["]", "n", "[", "h"])
    assert views == [("a", 0), ("b", 0)] and changes == 0  # nothing to undo either


def test_undo_and_redo_structure(keymap):
    text = "- a\n- b\n- c\n"
    views, cursor, _ = ops(keymap, text, ["n", "]", "n", "z", "h", "h"])
    assert views == [("a", 0), ("b", 0), ("c", 0)] and cursor == "b"
    views, cursor, _ = ops(keymap, text, ["n", "]", "n", "z", "h", "h", "t"])
    assert views == [("a", 0), ("b", 1), ("c", 0)] and cursor == "b"


def test_undo_whole_edit_session_including_splits(keymap):
    keys = ["d", *keys_for("x"), "ctrl+b", *keys_for("y"), "ctrl+g"]
    views, _, _ = ops(keymap, "- a\n", keys)
    assert views == [("ax", 0), ("y", 0)]
    views, cursor, _ = ops(keymap, "- a\n", [*keys, "h"])
    assert views == [("a", 0)] and cursor == "a"
    views, _, _ = ops(keymap, "- a\n", [*keys, "h", "t"])
    assert views == [("ax", 0), ("y", 0)]


def test_unchanged_edit_is_not_an_undo_step(keymap):
    views, _, _ = ops(keymap, "- a\n- b\n", ["z", "s", "ctrl+g", "h"])
    assert views == [("a", 0), ("b", 0)]  # the undo reverted the delete, not the no-op edit


def test_new_change_clears_redo(keymap):
    views, _, _ = ops(keymap, "- a\n- b\n", ["z", "h", "n", "z", "t"])
    assert views == [("a", 0)]


def test_undo_with_nothing_to_undo(keymap):
    views, _, changes = ops(keymap, "- a\n", ["h", "t"])
    assert views == [("a", 0)] and changes == 0


def test_block_ops_are_text_in_edit_mode(keymap):
    views, _, _ = ops(keymap, "- a\n", ["d", "z", "]", "h", "ctrl+g"])
    assert views == [("az]h", 0)]


# --- New blocks (tests/fixtures/keybinds.yaml): v below, b above. ---


def test_new_block_below_is_first_child_when_there_are_children(keymap):
    views, cursor, _ = ops(keymap, TEXT, ["v", *keys_for("new"), "ctrl+g"])
    assert views == [("a", 0), ("new", 1), ("b\nmore", 1), ("c", 2), ("d", 0)] and cursor == "new"


def test_new_block_below_leaf_is_next_sibling(keymap):
    views, cursor, _ = ops(keymap, TEXT, ["n", "n", "v", *keys_for("new"), "ctrl+g"])
    assert views == [("a", 0), ("b\nmore", 1), ("c", 2), ("new", 2), ("d", 0)] and cursor == "new"


def test_new_block_above_and_edits(keymap):
    views, cursor, _ = ops(keymap, TEXT, ["n", "b", *keys_for("new"), "ctrl+g"])
    assert views[:3] == [("a", 0), ("new", 1), ("b\nmore", 1)] and cursor == "new"


def test_new_block_starts_in_edit_mode(keymap):
    _, focused, editor_text, block = edit(keymap, TEXT, ["v"])
    assert focused is BlockEditor and editor_text == "" and block.content == ""


def test_new_empty_block_is_kept_and_saved(keymap):
    views, _, changes = ops(keymap, "- a\n", ["v", "ctrl+g"])
    assert views == [("a", 0), ("", 0)] and changes == 1


def test_new_block_and_its_text_are_one_undo_step(keymap):
    views, cursor, _ = ops(keymap, "- a\n", ["v", *keys_for("x"), "ctrl+g", "h"])
    assert views == [("a", 0)] and cursor == "a"


def test_new_block_on_empty_page(keymap):
    views, _, _ = ops(keymap, "", ["b", *keys_for("x"), "ctrl+g"])
    assert views == [("x", 0)]


def test_guide_follows_ancestry_to_top_level(keymap):
    # a > [b > [c > [e]], x]: cursor on e, so the path is e -> c -> b -> a.
    text = "- a\n\t- b\n\t\t- c\n\t\t\t- e\n\t- x\n- d\n"
    assert guide(keymap, text, ["n", "n", "n"]) == [
        (None, False, True, True),  # a: top of the path
        (0, True, True, True),  # b: turned in from a, stems down to c
        (2, True, True, True),  # c: turned in from b, stems down to e
        (4, True, True, False),  # e: cursor, turned in from c
        (None, False, False, False),  # x: off the path
        (None, False, False, False),  # d
    ]
