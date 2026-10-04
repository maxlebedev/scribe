from rich.syntax import Syntax
from rich.text import Text

from app.model import Block
from app.render import (
    CODE_STYLE,
    LINK_STYLE,
    MARKER_STYLES,
    PROPERTY_STYLE,
    render_block,
    render_page_properties,
)


def spans(text: Text) -> list[tuple[str, str]]:
    return [(text.plain[s.start : s.end], str(s.style)) for s in text.spans]


def render_text(content: str) -> Text:
    [part] = render_block(Block(content=content))
    return part


def test_plain_block_unstyled():
    assert spans(render_text("just text\nmore")) == []


def test_open_task_marker():
    assert spans(render_text("TODO buy milk")) == [("TODO", MARKER_STYLES["TODO"])]


def test_finished_task_struck_through():
    assert spans(render_text("DONE plan\nnotes")) == [
        ("DONE", MARKER_STYLES["DONE"]),
        (" plan", "dim strike"),
    ]


def test_marker_must_be_a_word_at_start():
    assert spans(render_text("TODOS are fun")) == []
    assert spans(render_text("a TODO later")) == []


def test_properties_dimmed():
    assert spans(render_text("title\nid:: 1\ntype:: note\nbody")) == [
        ("id:: 1", PROPERTY_STYLE),
        ("type:: note", PROPERTY_STYLE),
    ]


def test_links_highlighted_but_not_in_inline_code():
    assert spans(render_text("see [[A]], #tag and `[[code]]`")) == [
        ("`[[code]]`", CODE_STYLE),
        ("[[A]]", LINK_STYLE),
        ("#tag", LINK_STYLE),
    ]


def test_links_in_properties_highlighted():
    assert ("[[x]]", LINK_STYLE) in spans(render_text("title\ntags:: [[x]]"))


def test_code_block_split_out_and_highlighted():
    before, code, after = render_block(Block(content="see:\n```python\nx = 1\n```\nafter"))
    assert before.plain == "see:" and after.plain == "after"
    assert isinstance(code, Syntax)
    assert code.code == "x = 1" and code.lexer.name == "Python"


def test_code_without_language():
    [code] = render_block(Block(content="~~~\n- not a [[link]]\n~~~"))
    assert code.code == "- not a [[link]]"


def test_unclosed_fence_rest_is_code():
    before, code = render_block(Block(content="a\n```\nb\nc"))
    assert before.plain == "a" and code.code == "b\nc"


def test_page_properties_dimmed():
    text = render_page_properties(["title:: Hi", "tags:: [[x]]"])
    assert text.plain == "title:: Hi\ntags:: [[x]]"
    assert ("[[x]]", LINK_STYLE) in spans(text)
    assert ("title:: Hi", PROPERTY_STYLE) in spans(text)


def test_every_marker_has_a_style():
    from app.model import MARKERS

    assert set(MARKER_STYLES) == set(MARKERS)
