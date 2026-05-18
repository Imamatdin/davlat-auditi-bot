"""Phone normalization, name/region validation, CSV serialization."""
from __future__ import annotations

import csv
import io
import re
from typing import Iterable, Optional

# Strip everything that is not a digit or leading plus.
_PHONE_STRIP_RE = re.compile(r"[^\d+]")
# Strict: letters (incl. Uzbek diacritics in Latin Extended), spaces, and the
# Uzbek apostrophe used in O', G'. No digits, no URL characters, no hyphens.
_NAME_VALID_RE = re.compile(r"^[A-Za-zÀ-ɏ'\s]+$")
_NAME_MIN_LEN = 5


def normalize_phone(raw: str) -> Optional[str]:
    """Return E.164 +998XXXXXXXXX or None.

    Accepts only Uzbek numbers, in one of these input shapes:
      +998901234567
      998901234567
      901234567 (9-digit national)

    Anything else (including the obsolete 8XXXXXXXXXX legacy form, which
    overlaps with Kazakh national numbers) is rejected.
    """
    if not raw:
        return None
    cleaned = _PHONE_STRIP_RE.sub("", raw.strip())
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    if not cleaned.isdigit():
        return None

    if cleaned.startswith("998") and len(cleaned) == 12:
        national = cleaned[3:]
    elif len(cleaned) == 9:
        national = cleaned
    else:
        return None

    # National part must be exactly 9 digits, leading digit non-zero.
    if len(national) != 9 or national[0] == "0":
        return None

    return "+998" + national


def validate_name(raw: str) -> bool:
    """True iff `raw` looks like a real Uzbek full name.

    Rules: minimum 5 characters after whitespace collapse, must contain at
    least one space (so ism + familiya both present), and only letters,
    spaces, and the Uzbek apostrophe. Blocks digits, URLs, @mentions, etc.
    """
    name = " ".join(raw.split())
    if len(name) < _NAME_MIN_LEN:
        return False
    if " " not in name:
        return False
    if not _NAME_VALID_RE.match(name):
        return False
    return True


def clean_name(raw: str) -> str:
    return " ".join(raw.split())


def clean_region(raw: str) -> str:
    return " ".join(raw.split())


def is_region_valid(raw: str) -> bool:
    return len(clean_region(raw)) >= 3


_CSV_INJECTION_PREFIXES = ("=", "+", "-", "@")


def _csv_escape(cell: str) -> str:
    """Defuse Excel/Sheets formula injection.

    A cell that opens with =, +, -, or @ is interpreted as a formula by
    Excel and Google Sheets. A student named "=HYPERLINK(...)" or
    "=cmd|'/c calc'!A1" can therefore execute on the admin's machine when
    the CSV is opened. Prefixing such cells with a single quote forces them
    to be treated as text.
    """
    if cell and cell[0] in _CSV_INJECTION_PREFIXES:
        return "'" + cell
    return cell


def build_students_csv(rows: Iterable[list[str]]) -> bytes:
    """Serialize rows (first row = header) to UTF-8 CSV bytes with BOM.

    The BOM makes Excel on Windows pick up UTF-8 correctly so Cyrillic /
    Uzbek diacritics render in admin spreadsheets. Header row is written
    as-is; data rows are passed through _csv_escape.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    rows = list(rows)
    if rows:
        writer.writerow(rows[0])
        for row in rows[1:]:
            writer.writerow([_csv_escape(c) for c in row])
    return ("﻿" + buf.getvalue()).encode("utf-8")
