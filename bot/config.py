"""Configuration loaded from environment variables.

Fails fast on missing required values so deploy mistakes surface at startup
instead of mid-conversation.
"""
from __future__ import annotations

import os
from typing import FrozenSet


def _load_admin_ids(raw: str) -> FrozenSet[int]:
    ids = set()
    for piece in raw.split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            ids.add(int(piece))
        except ValueError as exc:
            raise RuntimeError(
                f"ADMIN_IDS contains non-integer value: {piece!r}"
            ) from exc
    return frozenset(ids)


BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required.")

ADMIN_IDS: FrozenSet[int] = _load_admin_ids(os.environ.get("ADMIN_IDS", ""))
if not ADMIN_IDS:
    raise RuntimeError(
        "ADMIN_IDS environment variable is required "
        "(comma-separated Telegram user IDs)."
    )

PORT: int = int(os.environ.get("PORT", "8080"))
DB_PATH: str = os.environ.get("DB_PATH", "davlat_auditi.db")

# One-off DB restore: when set, exposes a token-protected PUT /restore endpoint
# that swaps the SQLite file on the volume. Leave UNSET in normal operation;
# set it only while restoring, then unset it again.
RESTORE_TOKEN: str = os.environ.get("RESTORE_TOKEN", "").strip()

# Broadcast pacing: ~20 msg/sec is safe under Telegram's global limits.
BROADCAST_DELAY_SECONDS: float = 0.05

# Bakalavr / Magistratura caps (informational, not enforced).
CAP_BAKALAVR: int = 200
CAP_MAGISTRATURA: int = 30
