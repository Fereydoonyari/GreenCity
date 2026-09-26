"""Password hashing port – keeps crypto details out of domain entities."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class PasswordHasher(Protocol):
    """Hash and verify user passwords."""

    def hash(self, plain_password: str) -> str:
        """Return a one-way hash of ``plain_password``."""

        ...

    def verify(self, plain_password: str, password_hash: str) -> bool:
        """Return ``True`` if ``plain_password`` matches ``password_hash``."""

        ...
