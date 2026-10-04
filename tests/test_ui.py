import asyncio
from datetime import date

from textual.widgets import Static

from app.config import Config
from app.outline import Outline
from app.ui import ModeLine, ScribeApp

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
