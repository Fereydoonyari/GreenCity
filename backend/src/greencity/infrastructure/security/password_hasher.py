"""Bcrypt-based password hasher implementing ``PasswordHasher``."""

from __future__ import annotations

import bcrypt


class BcryptPasswordHasher:
    """Hash and verify passwords using bcrypt."""

    def hash(self, plain_password: str) -> str:
        """Return a bcrypt hash for ``plain_password``."""

        hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
        return hashed.decode("utf-8")

    def verify(self, plain_password: str, password_hash: str) -> bool:
        """Return ``True`` when the password matches the stored hash."""

        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
