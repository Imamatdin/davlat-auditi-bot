"""Phone normalization, name/region validation, CSV serialization."""
from __future__ import annotations

import csv
import io
import re
from typing import Iterable, Optional

# Strip everything that is not a digit or leading plus.
_PHONE_STRIP_RE = re.compile(r"[^\d+]")
# Names allow Uzbek Latin letters (incl. apostrophe), spaces, hyphens, dots.
# We deliberately keep this permissive: school staff will trust submitted data.
_NAME_VALID_RE = re.compile(r"^[A-Za-zÀ-ɏ'`\-.\s]+$")


def normalize_phone(raw: str) -> Optional[str]:
    """Return E.164 +998XXXXXXXXX or None if not a valid Uzbek number.

    Accepts:
      +998901234567
      998901234567
      901234567 (9-digit local)
      80901234567 (with leading 8, occasionally seen)
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
    elif len(cleaned) == 10 and cleaned.startswith("8"):
        # Legacy form: drop the leading 8.
        national = cleaned[1:]
    else:
        return None

    # Uzbek mobile/landline operator prefix: 2 digits, first digit 1-9.
    if not (national[0].isdigit() and national[0] != "0"):
        return None

    return "+998" + national


def validate_name(raw: str) -> tuple[bool, Optional[str]]:
    """Return (ok, error_key). error_key is 'short' or 'invalid' when not ok."""
    name = " ".join(raw.split())
    if len(name) < 3:
        return False, "short"
    if not _NAME_VALID_RE.match(name):
        return False, "invalid"
    return True, None


def clean_name(raw: str) -> str:
    return " ".join(raw.split())


def clean_region(raw: str) -> str:
    return " ".join(raw.split())


def is_region_valid(raw: str) -> bool:
    return len(clean_region(raw)) >= 3


def build_students_csv(rows: Iterable[list[str]]) -> bytes:
    """Serialize rows (first row = header) to UTF-8 CSV bytes with BOM.

    The BOM makes Excel on Windows pick up UTF-8 correctly so Cyrillic /
    Uzbek diacritics render in admin spreadsheets.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    for row in rows:
        writer.writerow(row)
    return ("﻿" + buf.getvalue()).encode("utf-8")
