from app.store import load_page, page_path


def test_page_path_uses_filename_mapping(tmp_path):
    assert page_path(tmp_path, "2026-10-04") == tmp_path / "2026_10_04.md"
    assert page_path(tmp_path, "proj/sub") == tmp_path / "proj___sub.md"


def test_load_existing_page(tmp_path):
    (tmp_path / "2026_10_04.md").write_text("- a\n\t- b\n")
    page = load_page(tmp_path, "2026-10-04")
    assert page.name == "2026-10-04"
    assert [(b.content, d) for b, d in page.walk()] == [("a", 0), ("b", 1)]


def test_load_missing_page_creates_empty_file(tmp_path):
    page = load_page(tmp_path, "proj/sub")
    assert page.name == "proj/sub" and page.blocks == []
    assert (tmp_path / "proj___sub.md").read_text() == ""


def test_load_leaves_existing_file_alone(tmp_path):
    (tmp_path / "Page.md").write_text("- keep me\n")
    load_page(tmp_path, "Page")
    assert (tmp_path / "Page.md").read_text() == "- keep me\n"
