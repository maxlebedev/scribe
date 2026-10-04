import asyncio

from textual.app import App
from textual.widgets import Static

from app.markdown import parse
from app.outline import BlockView, Outline

TEXT = "- a\n\t- b\n\t  more\n\t\t- c\n- d\n"


class Host(App):
    def __init__(self, text, keymap):
        super().__init__()
        self.page = parse(text)
        self.set_keymap(keymap)

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
                [v.styles.padding.left for v in views],
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
