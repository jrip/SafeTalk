from __future__ import annotations

from datetime import datetime, timezone
from typing import NewType
from uuid import UUID

ID = NewType("ID", UUID)
UTCDateTime = datetime


def now_utc() -> UTCDateTime:
    return datetime.now(timezone.utc)
