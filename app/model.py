"""In-memory page/block tree. Block text is the source of truth; everything else is derived."""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field

MARKERS = ("TODO", "DOING", "DONE", "LATER", "NOW", "WAITING", "CANCELED")

PROPERTY = re.compile(r"^([A-Za-z0-9_-]+)::(?:[ \t](.*))?$")
_MARKER = re.compile(rf"^({'|'.join(MARKERS)})(?:\s|$)")


def parse_property(line: str) -> tuple[str, str] | None:
    m = PROPERTY.match(line)
    return (m[1].lower(), (m[2] or "").strip()) if m else None


@dataclass(eq=False)
class Block:
    content: str = ""
    children: list[Block] = field(default_factory=list)
    parent: Block | None = field(default=None, repr=False)
    # Ephemeral: regenerated on every parse, never written to disk.
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @property
    def first_line(self) -> str:
        return self.content.split("\n", 1)[0]

    @property
    def marker(self) -> str | None:
        m = _MARKER.match(self.first_line)
        return m[1] if m else None

    @property
    def properties(self) -> dict[str, str]:
        """`key:: value` lines directly after the first line (or from the first line on)."""
        lines = self.content.split("\n")
        start = 0 if parse_property(lines[0]) else 1
        props = {}
        for line in lines[start:]:
            prop = parse_property(line)
            if prop is None:
                break
            props[prop[0]] = prop[1]
        return props

    def add_child(self, child: Block, index: int | None = None) -> None:
        child.parent = self
        self.children.insert(len(self.children) if index is None else index, child)

    def walk(self, depth: int = 0) -> Iterator[tuple[Block, int]]:
        yield self, depth
        for child in self.children:
            yield from child.walk(depth + 1)


@dataclass(eq=False)
class Page:
    name: str = ""
    # Page-level `key:: value` lines at the top of the file, kept verbatim.
    property_lines: list[str] = field(default_factory=list)
    blocks: list[Block] = field(default_factory=list)
    # One level of block indentation as written in the file (Logseq default: tab).
    indent: str = "\t"

    @property
    def properties(self) -> dict[str, str]:
        return dict(p for line in self.property_lines if (p := parse_property(line)))

    def walk(self) -> Iterator[tuple[Block, int]]:
        for block in self.blocks:
            yield from block.walk()
