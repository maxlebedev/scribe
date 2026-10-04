import pytest

from app.store import load_page, page_path, save_page


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


def test_save_writes_serialized_page(tmp_path):
    (tmp_path / "Page.md").write_text("- a\n\t- b\n")
    page = load_page(tmp_path, "Page")
    page.blocks[0].children[0].content = "b edited"
    save_page(tmp_path, page)
    assert (tmp_path / "Page.md").read_text() == "- a\n\t- b edited\n"
    assert [p.name for p in tmp_path.iterdir()] == ["Page.md"]  # no temp file left


def test_save_keeps_file_mode(tmp_path):
    path = tmp_path / "Page.md"
    path.write_text("- a\n")
    path.chmod(0o640)
    save_page(tmp_path, load_page(tmp_path, "Page"))
    assert path.stat().st_mode & 0o777 == 0o640


def test_failed_save_leaves_old_file_and_no_temp(tmp_path, monkeypatch):
    path = tmp_path / "Page.md"
    path.write_text("- old\n")
    page = load_page(tmp_path, "Page")
    page.blocks[0].content = "new"

    def boom(*args):
        raise OSError("disk full")

    monkeypatch.setattr("app.store.os.replace", boom)
    with pytest.raises(OSError):
        save_page(tmp_path, page)
    assert path.read_text() == "- old\n"
    assert [p.name for p in tmp_path.iterdir()] == ["Page.md"]
