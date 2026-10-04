import pytest

from app.links import extract_refs


@pytest.mark.parametrize(
    "text,refs",
    [
        ("see [[Some Page]]", ["Some Page"]),
        ("#tag and #other-tag", ["tag", "other-tag"]),
        ("#[[multi word]]", ["multi word"]),
        ("end of sentence #tag.", ["tag"]),
        ("(#paren)", ["paren"]),
        ("[[A]] then [[a]] and [[A]] again", ["A", "a"]),
        ("namespaced [[proj/sub]]", ["proj/sub"]),
        ("# heading, not a tag", []),
        ("## heading", []),
        ("C# or url.com/#frag", []),
        ("`[[in inline code]]` and [[real]]", ["real"]),
        ("```\n[[in fence]] #nope\n```\n#yes", ["yes"]),
        ("[[]] empty", []),
        ("multi\nline [[x]]\n#y", ["x", "y"]),
    ],
)
def test_extract_refs(text, refs):
    assert extract_refs(text) == refs
