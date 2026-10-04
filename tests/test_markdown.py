import pytest

from app.markdown import parse, serialize

CANONICAL = {
    "empty": "",
    "single": "- hello\n",
    "empty block": "-\n",
    "siblings": "- one\n- two\n- three\n",
    "nested tabs": "- a\n\t- b\n\t\t- c\n\t- d\n- e\n",
    "nested 2 spaces": "- a\n  - b\n    - c\n",
    "nested 4 spaces": "- a\n    - b\n        - c\n",
    "multi-line": "- first line\n  second line\n\n  new paragraph\n",
    "multi-line nested": "- a\n\t- b line 1\n\t  b line 2\n",
    "page properties": "title:: My Page\ntags:: foo, bar\n\n- first\n",
    "only page properties": "title:: x\n",
    "code block": "- see:\n  ```python\n  def f():\n      return 1\n  ```\n",
    "code block with blank line": "- ```\n  a\n\n  b\n  ```\n",
    "code starting on bullet line": "- ```js\n  x()\n  ```\n",
    "code with bullet-like lines": "- ```\n  - not a block\n  * nor this\n  ```\n- real\n",
    "tilde fence": "- ~~~\n  - still code\n  ~~~\n",
    "trailing spaces kept": "- line with hard break  \n  next\n",
}


@pytest.mark.parametrize("text", CANONICAL.values(), ids=CANONICAL.keys())
def test_canonical_round_trip(text):
    assert serialize(parse(text)) == text


def tree(page):
    return [(depth, b.content) for b, depth in page.walk()]


def test_structure():
    page = parse("- a\n\t- b\n\t  more\n\t\t- c\n- d\n")
    assert tree(page) == [(0, "a"), (1, "b\nmore"), (2, "c"), (0, "d")]
    b = page.blocks[0].children[0]
    assert b.parent is page.blocks[0]
    assert page.blocks[0].parent is None


def test_code_fence_hides_bullets():
    page = parse("- ```\n  - x\n  ```\n- y\n")
    assert tree(page) == [(0, "```\n- x\n```"), (0, "y")]


def test_code_relative_indent_preserved():
    page = parse("- a\n\t- ```\n\t      indented\n\t  ```\n")
    assert page.blocks[0].children[0].content == "```\n    indented\n```"


def test_page_properties():
    page = parse("title:: Hello\nAlias:: hi\n\n- x\n")
    assert page.properties == {"title": "Hello", "alias": "hi"}
    assert tree(page) == [(0, "x")]


def test_ids_unique_and_ephemeral():
    text = "- a\n- b\n"
    ids1 = [b.id for b, _ in parse(text).walk()]
    ids2 = [b.id for b, _ in parse(text).walk()]
    assert len(set(ids1)) == 2
    assert not set(ids1) & set(ids2)


# --- Normalization: non-canonical input is tidied, never loses text. ---

NORMALIZE = {
    "crlf": ("- a\r\n\t- b\r\n", "- a\n\t- b\n"),
    "star and plus bullets": ("* a\n+ b\n", "- a\n- b\n"),
    "missing trailing newline": ("- a", "- a\n"),
    "blank lines between blocks": ("- a\n\n\n- b\n\n", "- a\n- b\n"),
    "lazy continuation": ("- a\ntyped on phone\n", "- a\n  typed on phone\n"),
    "stray preamble text": ("some text\n\n- a\n", "- some text\n- a\n"),
    "plain markdown file": ("just a note\nsecond line\n", "- just a note\n  second line\n"),
    "props then text": ("k:: v\nhello\n- a\n", "k:: v\n\n- hello\n- a\n"),
    "uneven indent": ("- a\n   - b\n - c\n", "- a\n   - b\n   - c\n"),
    "trailing space bullet": ("- \n", "-\n"),
}


@pytest.mark.parametrize("text,expected", NORMALIZE.values(), ids=NORMALIZE.keys())
def test_normalize(text, expected):
    assert serialize(parse(text)) == expected


MESSY = [
    "intro\n* one\n   two\n\t\t- deep\n- ```\ncode - x\n```\nafter\n+ last",
    "- a\n\t\t\t- skipped levels\n\t- back\n",
    "- ```\n  unclosed fence\n- swallowed as code\n",
    "title:: t\n\n\n\n-\n-\n- x\n\n",
]


@pytest.mark.parametrize("text", MESSY)
def test_no_text_lost(text):
    out = serialize(parse(text))
    for line in text.splitlines():
        body = line.strip().lstrip("-*+").strip()
        assert body in out, f"lost: {line!r}"


@pytest.mark.parametrize("text", MESSY)
def test_serialize_is_stable(text):
    once = serialize(parse(text))
    assert serialize(parse(once)) == once
