import pytest

from app.model import Block


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
