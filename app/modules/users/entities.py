from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class User:
    """Plain data model for Users domain."""

    email: str
    password_hash: str
    name: str
    role: str = "user"
    allow_negative_balance: bool = False
    id: UUID = field(default_factory=uuid4)
