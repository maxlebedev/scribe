"""Command-line entry point."""

import argparse
import sys

from app.config import config_path, load_config


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="scribe", description="Logseq-style block outliner for the terminal.")
    parser.add_argument(
        "notes_dir",
        nargs="?",
        help=f"notes directory (default: notes_dir from {config_path()}, else ~/notes)",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.notes_dir)
    except (OSError, ValueError) as e:  # tomllib.TOMLDecodeError is a ValueError
        sys.exit(f"scribe: {e}")

    from app.ui import ScribeApp  # deferred: keeps --help fast

    ScribeApp(config).run()
