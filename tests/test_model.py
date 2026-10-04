import pytest

from app.model import Block, Page


@pytest.mark.parametrize(
    "content,marker",
    [
        ("TODO buy milk", "TODO"),
        ("DONE", "DONE"),
        ("DOING x\nmore", "DOING"),
        ("TODOS are fun", None),
        ("todo lowercase", None),
        ("a TODO later", None),
    ],
)
def test_marker(content, marker):
    assert Block(content=content).marker == marker


def test_properties_after_first_line():
    b = Block(content="title\nid:: 1\nType:: note\nbody\nlate:: ignored")
    assert b.properties == {"id": "1", "type": "note"}


def test_properties_only_block():
    assert Block(content="a:: 1\nb::").properties == {"a": "1", "b": ""}


def test_no_properties():
    assert Block(content="just text\nmore text").properties == {}


def test_add_child_sets_parent():
    parent, child = Block(content="p"), Block(content="c")
    parent.add_child(child)
    assert child.parent is parent and parent.children == [child]


def test_insert_after_top_level_and_nested():
    a, b, child, new_top, new_child = (Block(content=c) for c in "a b c X Y".split())
    page = Page(blocks=[a, b])
    a.add_child(child)
    page.insert_after(a, new_top)
    page.insert_after(child, new_child)
    assert page.blocks == [a, new_top, b] and new_top.parent is None
    assert a.children == [child, new_child] and new_child.parent is a
