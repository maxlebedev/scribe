import asyncio
from datetime import date

from textual.widgets import Static

from app.config import Config
from app.outline import Outline
from app.ui import ScribeApp

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
