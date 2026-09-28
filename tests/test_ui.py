import asyncio

from app.ui import ScribeApp
from app.config import Config


def test_app_starts_and_quits(tmp_path):
    async def run():
        app = ScribeApp(Config(notes_dir=tmp_path))
        async with app.run_test() as pilot:
            await pilot.press("q")
        assert app.return_code == 0

    asyncio.run(run())
