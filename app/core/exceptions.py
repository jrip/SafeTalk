class DomainError(Exception):
    """Base exception for business-domain violations."""


class ValidationError(DomainError):
    """Raised when entity invariants are violated."""


class NotFoundError(DomainError):
    """Raised when requested entity is missing."""


class InsufficientBalanceError(DomainError):
    """Raised when debit operation cannot be applied."""
