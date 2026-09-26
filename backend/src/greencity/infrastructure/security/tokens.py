"""HS256 JWT access-token implementation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from greencity.domain.exceptions import UnauthorizedError


class JwtAccessTokenService:
    """Create and parse GreenCity access tokens."""

    def __init__(self, *, secret: str, expire_minutes: int = 60 * 24 * 7) -> None:
        if not secret.strip():
            raise ValueError("JWT secret must not be empty.")
        self._secret = secret
        self._expire_minutes = max(5, expire_minutes)
        self._algorithm = "HS256"

    def create_access_token(self, user_id: UUID, email: str) -> str:
        """Return a signed access token for ``user_id``."""

        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "email": email,
            "iat": now,
            "exp": now + timedelta(minutes=self._expire_minutes),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def parse_user_id(self, token: str) -> UUID:
        """Return the subject user id or raise ``UnauthorizedError``."""

        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("Invalid or expired access token.") from exc

        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            raise UnauthorizedError("Invalid access token subject.")
        try:
            return UUID(subject)
        except ValueError as exc:
            raise UnauthorizedError("Invalid access token subject.") from exc
