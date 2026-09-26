"""Domain-level exceptions.

Presentation and infrastructure layers map these to HTTP status codes
or infrastructure errors without leaking transport concerns into domain.
"""


class DomainError(Exception):
    """Base class for all domain errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(DomainError):
    """Raised when a requested aggregate or entity does not exist."""


class ValidationError(DomainError):
    """Raised when domain invariants are violated."""


class ConflictError(DomainError):
    """Raised when an operation conflicts with current state."""


class UnauthorizedError(DomainError):
    """Raised when authentication is missing or invalid."""


class ForbiddenError(DomainError):
    """Raised when the authenticated user may not perform the action."""
