"""Markdown file <-> Page.

Canonical (Logseq-style) files round-trip byte for byte. Anything else, e.g. files touched
by a mobile editor, is normalized without dropping text: stray paragraphs become blocks,
lazy (unindented) continuation lines join the block above, `*`/`+` bullets become `-`.
"""

import re

from app.model import Block, Page, parse_property

TAB_WIDTH = 4
BULLET = re.compile(r"^([ \t]*)[-*+](?:[ \t](.*))?$")
_FENCE_OPEN = re.compile(r"^\s*(`{3,}|~{3,})")


class FenceTracker:
    """Tracks whether we're inside a ``` / ~~~ code fence, line by line."""

    def __init__(self) -> None:
        self.marker: str | None = None

    def feed(self, line: str) -> None:
        stripped = line.strip()
        if self.marker is None:
            if m := _FENCE_OPEN.match(line):
                self.marker = m[1]
        elif stripped.startswith(self.marker) and not stripped.lstrip(self.marker[0]):
            self.marker = None

    @property
    def inside(self) -> bool:
        return self.marker is not None


def _width(ws: str) -> int:
    return sum(TAB_WIDTH if c == "\t" else 1 for c in ws)


def _strip_indent(line: str, width: int) -> str:
    """Remove up to `width` columns of leading whitespace."""
    used = 0
    for i, c in enumerate(line):
        step = TAB_WIDTH if c == "\t" else 1 if c == " " else None
        if step is None or used + step > width:
            return line[i:]
        used += step
    return ""


def _trim_blank_edges(lines: list[str]) -> list[str]:
    start, end = 0, len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def parse(text: str, name: str = "") -> Page:
    page = Page(name=name)
    lines = text.splitlines()

    # Preamble: everything before the first bullet.
    i = 0
    while i < len(lines) and not BULLET.match(lines[i]):
        i += 1
    preamble = _trim_blank_edges(lines[:i])
    n_props = 0
    while n_props < len(preamble) and parse_property(preamble[n_props]):
        n_props += 1
    page.property_lines = preamble[:n_props]
    if stray := _trim_blank_edges(preamble[n_props:]):
        page.blocks.append(Block(content="\n".join(stray)))

    stack: list[tuple[int, Block]] = []  # (bullet indent width, block)
    block_lines: dict[Block, list[str]] = {}
    content_width = 0
    fence = FenceTracker()
    indent_seen = False

    for line in lines[i:]:
        m = BULLET.match(line)
        if m and not fence.inside:
            ws, first = m[1], m[2] or ""
            width = _width(ws)
            while stack and stack[-1][0] >= width:
                stack.pop()
            block = Block()
            if stack:
                stack[-1][1].add_child(block)
                if not indent_seen and len(stack) == 1:
                    page.indent, indent_seen = ws, True
            else:
                page.blocks.append(block)
            stack.append((width, block))
            block_lines[block] = [first]
            content_width = width + 2
            fence = FenceTracker()
            fence.feed(first)
            continue
        body = _strip_indent(line, content_width)
        block_lines[stack[-1][1]].append(body)
        fence.feed(body)

    for block, blines in block_lines.items():
        block.content = "\n".join([blines[0], *_trim_blank_edges(blines[1:])]).rstrip("\n")
    return page


def serialize(page: Page) -> str:
    out = list(page.property_lines)
    if out and page.blocks:
        out.append("")
    for block, depth in page.walk():
        ws = page.indent * depth
        first, *rest = block.content.split("\n")
        out.append(f"{ws}- {first}" if first else f"{ws}-")
        out.extend(f"{ws}  {line}" if line else "" for line in rest)
    return "\n".join(out) + "\n" if out else ""
