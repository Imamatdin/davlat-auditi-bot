"""Phone normalization, name/region validation, CSV serialization,
relative-time rendering, and FAQ keyword matching."""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
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


def humanize_age(created_at_iso: str) -> str:
    """Render how long ago `created_at_iso` (a UTC ISO timestamp) was, in Uzbek.

    Buckets: hozirgina (<1 min), N daqiqa/soat/kun oldin. Returns "" if the
    timestamp cannot be parsed.
    """
    try:
        created = datetime.fromisoformat(created_at_iso)
    except (ValueError, TypeError):
        return ""
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    secs = int((datetime.now(timezone.utc) - created).total_seconds())
    if secs < 60:
        return "hozirgina"
    minutes = secs // 60
    if minutes < 60:
        return f"{minutes} daqiqa oldin"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} soat oldin"
    days = hours // 24
    return f"{days} kun oldin"


# Word characters for FAQ matching: Unicode letters/digits plus the Uzbek
# apostrophe variants used in O', G'.
_FAQ_WORD_RE = re.compile(r"[\w'’]+", re.UNICODE)
# A storable keyword: 1..40 chars of letters/digits/space/hyphen/apostrophe.
# Excludes <, >, &, / so the keyword renders safely in the suggestion hint.
_FAQ_KEYWORD_RE = re.compile(r"^[\w'’ \-]{1,40}$", re.UNICODE)


def normalize_keyword(raw: str) -> str:
    """Lowercase and collapse whitespace so lookups are case/space insensitive."""
    return " ".join((raw or "").lower().split())


def is_valid_faq_keyword(keyword: str) -> bool:
    """True iff `keyword` (already normalized) is safe to store and display."""
    return bool(keyword) and bool(_FAQ_KEYWORD_RE.match(keyword))


def suggest_faq_keyword(text: str, keywords: Iterable[str]) -> Optional[str]:
    """Return the strongest matching FAQ keyword for `text`, or None.

    Single-word keywords (>= 3 chars) must hit a whole word in the text;
    multi-word keywords match as a substring. The longest matching keyword
    wins, since a longer keyword is a more specific (stronger) signal.
    """
    if not text:
        return None
    lowered = text.lower()
    tokens = set(_FAQ_WORD_RE.findall(lowered))
    best: Optional[str] = None
    best_len = 0
    for kw in keywords:
        k = (kw or "").strip().lower()
        if not k:
            continue
        if " " in k:
            matched = k in lowered
        else:
            matched = len(k) >= 3 and k in tokens
        if matched and len(k) > best_len:
            best, best_len = kw, len(k)
    return best


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
