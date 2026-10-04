from datetime import date

import pytest

from app.pages import filename_for, journal_date, journal_name, name_for, page_key


def test_journal_naming():
    assert journal_name(date(2026, 9, 27)) == "2026-09-27"
    assert filename_for("2026-09-27") == "2026_09_27.md"
    assert name_for("2026_09_27.md") == "2026-09-27"
    assert journal_date("2026-09-27") == date(2026, 9, 27)
    assert journal_date("2026-02-30") is None


@pytest.mark.parametrize(
    "name,filename",
    [
        ("Simple Page", "Simple Page.md"),
        ("proj/sub", "proj___sub.md"),
        ("what?", "what%3F.md"),
        ("a:b", "a%3Ab.md"),
        ("100%", "100%25.md"),
        (".hidden", "%2Ehidden.md"),
        ("ends with dot.", "ends with dot%2E.md"),
    ],
)
def test_filename_for(name, filename):
    assert filename_for(name) == filename


@pytest.mark.parametrize(
    "name",
    [
        "Simple", "proj/sub/deep", "a_b", "a___b", "a_/b", "a/_b", "x/__y", "2026_09_27",
        "2026-02-30", "what?*<>|\"\\:", "50%", "%2F", ".dot", "dot.", "space ", "Ünïcødé",
        "tab\there",
    ],
)
def test_name_round_trip(name):
    assert name_for(filename_for(name)) == name.strip()


def test_page_key_case_sensitive():
    assert page_key("  My Page ") == page_key("My Page")
    assert page_key("My Page") != page_key("my page")


def test_empty_name_rejected():
    with pytest.raises(ValueError):
        filename_for("  ")
