"""Block text -> Rich renderables: task markers, dimmed properties, links, code."""

import re

from rich.syntax import Syntax
from rich.text import Text

from app.links import INLINE_CODE, ref_spans
from app.markdown import FenceTracker
from app.model import Block, property_span

LINK_STYLE = "bold cyan"
CODE_STYLE = "bold magenta"
PROPERTY_STYLE = "dim"
MARKER_STYLES = {
    "TODO": "bold blue",
    "DOING": "bold yellow",
    "DONE": "bold green",
    "CANCELED": "bold bright_black",  # the palette's grey
}
FINISHED = {"DONE", "CANCELED"}  # rest of the first line is struck through
CODE_THEME = "ansi_dark"  # terminal palette colors, so it follows the terminal's theme

_FENCE_INFO = re.compile(r"^\s*(?:`{3,}|~{3,})\s*([^\s`]*)")


def render_block(block: Block) -> list[Text | Syntax]:
    """Text runs and syntax-highlighted code blocks, in order. Fence lines are not shown."""
    lines = block.content.split("\n")
    props = property_span(lines)
    parts: list[Text | Syntax] = []
    text: list[Text] = []
    code: list[str] = []
    lang = ""
    fence = FenceTracker()

    def flush_text() -> None:
        if text:
            parts.append(Text("\n").join(text))
            text.clear()

    for i, line in enumerate(lines):
        was_inside = fence.inside
        fence.feed(line)
        if not was_inside and fence.inside:  # opening fence
            flush_text()
            lang = _FENCE_INFO.match(line)[1]
        elif was_inside and not fence.inside:  # closing fence
            parts.append(_code(code, lang))
            code = []
        elif fence.inside:
            code.append(line)
        else:
            text.append(_line(line, marker=block.marker if i == 0 else None, dim=i in props))
    if fence.inside:  # unclosed fence: the rest of the block is code
        parts.append(_code(code, lang))
    flush_text()
    return parts


def render_page_properties(lines: list[str]) -> Text:
    """Page-level property lines, dimmed."""
    return Text("\n").join(_line(line, dim=True) for line in lines)


def _line(line: str, marker: str | None = None, dim: bool = False) -> Text:
    t = Text(line, style=PROPERTY_STYLE if dim else "")
    if marker:
        t.stylize(MARKER_STYLES[marker], 0, len(marker))
        if marker in FINISHED:
            t.stylize("dim strike", len(marker))
    for m in INLINE_CODE.finditer(line):
        t.stylize(CODE_STYLE, *m.span())
    for start, end in ref_spans(line):
        t.stylize(LINK_STYLE, start, end)
    return t


def _code(lines: list[str], lang: str) -> Syntax:
    return Syntax(
        "\n".join(lines), lang or "text", theme=CODE_THEME, background_color="default", word_wrap=True
    )
