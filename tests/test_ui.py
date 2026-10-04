import asyncio
from datetime import date

from textual.widgets import Static

from app.ui import ScribeApp
from app.config import Config

TODAY = date(2026, 10, 4)


def run_app(tmp_path, check):
    async def run():
        app = ScribeApp(Config(notes_dir=tmp_path), today=TODAY)
        async with app.run_test() as pilot:
            check(app)
            await pilot.press("q")
        assert app.return_code == 0

    asyncio.run(run())


def text_of(app, widget_id):
    return str(app.query_one(widget_id, Static).content)


def test_opens_todays_journal(tmp_path):
    (tmp_path / "2026_10_04.md").write_text("- see [[Some Page]]\n")

    def check(app):
        assert text_of(app, "#title") == "2026-10-04"
        assert "see [[Some Page]]" in text_of(app, "#body")

    run_app(tmp_path, check)


def test_missing_journal_is_created_empty(tmp_path):
    def check(app):
        assert text_of(app, "#title") == "2026-10-04"
        assert text_of(app, "#body") == "(empty page)"

    run_app(tmp_path, check)
    assert (tmp_path / "2026_10_04.md").read_text() == ""
