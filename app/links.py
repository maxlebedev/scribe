"""Extract `[[page]]`, `#tag` and `#[[multi word tag]]` references from block text."""

import re

from app.markdown import FenceTracker

_INLINE_CODE = re.compile(r"`[^`\n]*`")
_REF = re.compile(
    r"\[\[([^\[\]]+?)\]\]"  # [[page]]
    r"|(?<![^\s(])#(?:\[\[([^\[\]]+?)\]\]"  # #[[multi word]]; '#' must start a word
    r"|([^\s#\[\]()\",.!?;:'`]+))"  # #tag
)


def _without_code(text: str) -> str:
    fence = FenceTracker()
    kept = []
    for line in text.split("\n"):
        was_inside = fence.inside
        fence.feed(line)
        if not was_inside and not fence.inside:
            kept.append(_INLINE_CODE.sub("", line))
    return "\n".join(kept)


def extract_refs(text: str) -> list[str]:
    """Referenced page names in order of first appearance, deduplicated."""
    seen, refs = set(), []
    for m in _REF.finditer(_without_code(text)):
        name = next(g for g in m.groups() if g).strip()
        if name and name not in seen:
            seen.add(name)
            refs.append(name)
    return refs
