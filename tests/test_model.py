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


def page_of(text):
    from app.markdown import parse

    return parse(text)


def shape(page):
    return [(b.content, d) for b, d in page.walk()]


def find(page, content):
    return next(b for b, _ in page.walk() if b.content == content)


def test_remove_takes_children():
    page = page_of("- a\n\t- b\n- c\n")
    page.remove(find(page, "a"))
    assert shape(page) == [("c", 0)]


def test_indent_under_previous_sibling_as_last_child():
    page = page_of("- a\n\t- x\n- b\n\t- c\n")
    assert page.indent_block(find(page, "b"))
    assert shape(page) == [("a", 0), ("x", 1), ("b", 1), ("c", 2)]
    assert find(page, "b").parent is find(page, "a")


def test_indent_first_sibling_is_noop():
    page = page_of("- a\n\t- b\n")
    assert not page.indent_block(find(page, "b"))
    assert not page.indent_block(find(page, "a"))
    assert shape(page) == [("a", 0), ("b", 1)]


def test_outdent_adopts_following_siblings():
    page = page_of("- a\n\t- b\n\t\t- c\n\t- d\n\t- e\n- f\n")
    assert page.outdent_block(find(page, "b"))
    assert shape(page) == [("a", 0), ("b", 0), ("c", 1), ("d", 1), ("e", 1), ("f", 0)]
    assert find(page, "d").parent is find(page, "b") and find(page, "b").parent is None


def test_outdent_top_level_is_noop():
    page = page_of("- a\n")
    assert not page.outdent_block(find(page, "a"))


def test_outline_snapshot_round_trip():
    page = page_of("- a\n\t- b\n\t  more\n\t\t- c\n- d\n")
    snap = page.outline()
    page.remove(find(page, "a"))
    page.set_outline(snap)
    assert page.outline() == snap
    assert find(page, "c").parent is find(page, "b\nmore")
