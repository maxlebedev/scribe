"""Page name <-> filename. Flat directory; journals are `YYYY_MM_DD.md`, named `YYYY-MM-DD`."""

import re
import unicodedata
from datetime import date
from urllib.parse import quote, unquote

_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_JOURNAL_STEM = re.compile(r"^(\d{4})_(\d{2})_(\d{2})$")
# Unsafe on Windows/Android filesystems, or needed for our own escaping.
_UNSAFE = set('<>:"\\|?*%')


def page_key(name: str) -> str:
    """Identity for a page name: links are case-sensitive."""
    return unicodedata.normalize("NFC", name).strip()


def journal_date(name: str) -> date | None:
    if m := _ISO_DATE.match(name):
        try:
            return date(*map(int, m.groups()))
        except ValueError:
            return None
    return None


def journal_name(d: date) -> str:
    return d.isoformat()


def filename_for(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValueError("empty page name")
    if d := journal_date(name):
        return f"{d:%Y_%m_%d}.md"
    chars = [
        quote(c, safe="") if c in _UNSAFE or ord(c) < 32 else c
        for c in name
    ]
    stem = "".join(chars)
    # "/" is written as "___", so escape underscores that could merge with it,
    # and names that would look like a journal file.
    if "/" in name or "___" in name or _JOURNAL_STEM.match(stem):
        stem = stem.replace("_", "%5F")
    stem = stem.replace("/", "___")
    # Leading dot = hidden file; trailing dot/space is invalid on Windows.
    if stem[0] == ".":
        stem = "%2E" + stem[1:]
    if stem[-1] in ". ":
        stem = stem[:-1] + f"%{ord(stem[-1]):02X}"
    return stem + ".md"


def name_for(filename: str) -> str:
    stem = filename.removesuffix(".md")
    if m := _JOURNAL_STEM.match(stem):
        return "-".join(m.groups())
    return unquote(stem.replace("___", "/"))
