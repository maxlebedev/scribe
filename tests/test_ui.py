import asyncio
from datetime import date

from textual.widgets import Footer, Static

from app.config import Config
from app.outline import Outline
from app.ui import KeysScreen, ModeLine, ScribeApp

TODAY = date(2026, 10, 4)


def run_app(tmp_path, keymap, check):
    async def run():
        app = ScribeApp(Config(notes_dir=tmp_path), keymap, today=TODAY)
        async with app.run_test() as pilot:
            check(app)
            await pilot.press("x")  # quit
        assert app.return_code == 0

    asyncio.run(run())


def text_of(app, widget_id):
    return str(app.query_one(widget_id, Static).content)


def test_opens_todays_journal(tmp_path, keymap):
    (tmp_path / "2026_10_04.md").write_text("- see [[Some Page]]\n")

    def check(app):
        assert text_of(app, "#title") == "2026-10-04"
        assert app.query_one(Outline).cursor_block.content == "see [[Some Page]]"

    run_app(tmp_path, keymap, check)


def test_missing_journal_is_created_empty(tmp_path, keymap):
    def check(app):
        assert text_of(app, "#title") == "2026-10-04"
        assert str(app.query_one("#outline .empty", Static).content) == "(empty page)"

    run_app(tmp_path, keymap, check)
    assert (tmp_path / "2026_10_04.md").read_text() == ""


def test_mode_line_follows_mode(tmp_path, keymap):
    (tmp_path / "2026_10_04.md").write_text("- a\n")

    async def run():
        app = ScribeApp(Config(notes_dir=tmp_path), keymap, today=TODAY)
        async with app.run_test() as pilot:
            line = app.query_one(ModeLine)
            seen = [(text_of(app, "#mode"), line.has_class("-edit"))]
            await pilot.press("d")  # edit at end
            await pilot.pause()
            seen.append((text_of(app, "#mode"), line.has_class("-edit")))
            await pilot.press("ctrl+g")  # commit
            await pilot.pause()
            seen.append((text_of(app, "#mode"), line.has_class("-edit")))
            return seen

    assert asyncio.run(run()) == [("VIEW", False), ("EDIT", True), ("VIEW", False)]


def journal_after(tmp_path, keymap, text, keys):
    """Write today's journal, press `keys` in the app, return the file's text afterwards."""
    path = tmp_path / "2026_10_04.md"
    path.write_text(text)

    async def run():
        app = ScribeApp(Config(notes_dir=tmp_path), keymap, today=TODAY)
        async with app.run_test() as pilot:
            await pilot.press(*keys)
            await pilot.pause()

    asyncio.run(run())
    return path.read_text()


def test_committed_edit_is_saved(tmp_path, keymap):
    assert journal_after(tmp_path, keymap, "- a\n", ["d", "!", "ctrl+g"]) == "- a!\n"


def test_split_is_saved(tmp_path, keymap):
    assert journal_after(tmp_path, keymap, "- a\n", ["d", "ctrl+b", "b", "ctrl+g"]) == "- a\n- b\n"


def test_unchanged_edit_leaves_file_alone(tmp_path, keymap):
    messy = "* not canonical\n"  # a save would rewrite this as "- not canonical"
    assert journal_after(tmp_path, keymap, messy, ["d", "ctrl+g"]) == messy


def test_delete_and_undo_are_saved(tmp_path, keymap):
    assert journal_after(tmp_path, keymap, "- a\n- b\n", ["z"]) == "- b\n"
    assert journal_after(tmp_path, keymap, "- a\n- b\n", ["z", "h"]) == "- a\n- b\n"


def test_mode_line_has_no_key_hints(tmp_path, keymap):
    async def run():
        app = ScribeApp(Config(notes_dir=tmp_path), keymap, today=TODAY)
        async with app.run_test():
            return len(app.query(Footer))

    assert asyncio.run(run()) == 0


def test_help_key_shows_current_keys_and_view_mode_key_closes(tmp_path, keymap):
    async def run():
        app = ScribeApp(Config(notes_dir=tmp_path), keymap, today=TODAY)
        async with app.run_test() as pilot:
            await pilot.press("g")
            await pilot.pause()
            screen = app.screen
            table = screen.query_one(Static).content
            rows = list(zip(*(c._cells for c in table.columns)))
            await pilot.press("g")  # the help key doesn't close it
            await pilot.pause()
            still_open = type(app.screen)
            await pilot.press("ctrl+g")  # the to_view_mode key does
            await pilot.pause()
            return type(screen), rows, still_open, type(app.screen)

    screen, rows, still_open, after = asyncio.run(run())
    assert screen is KeysScreen and still_open is KeysScreen and after is not KeysScreen
    assert ("z", "Delete") in rows and ("^g", "Done") in rows and ("^b", "New block") in rows
    assert ("g", "Show keys") in rows and ("x", "Quit") in rows


def test_help_key_is_text_in_edit_mode(tmp_path, keymap):
    assert journal_after(tmp_path, keymap, "- a\n", ["d", "g", "ctrl+g"]) == "- ag\n"


def test_no_textual_default_keys(tmp_path, keymap):
    """Every key comes from the keymap: Textual's own bindings are all switched off."""
    from textual.widgets import TextArea

    def unnamed(app):
        return {b.binding.key for b in app.active_bindings.values() if not b.binding.id}

    async def run():
        app = ScribeApp(Config(notes_dir=tmp_path), keymap, today=TODAY)
        async with app.run_test() as pilot:
            view = unnamed(app)
            await pilot.press("d")  # edit mode: the text box's bindings are active too
            await pilot.pause()
            return view, unnamed(app)

    view, edit = asyncio.run(run())
    assert view == set()
    # Only the text box's built-in editing keys have no id (Textual gives them none).
    assert edit <= set(TextArea._merged_bindings.key_to_bindings)  # incl. inherited scroll keys
