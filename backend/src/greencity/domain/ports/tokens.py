"""JWT / access-token port – keeps crypto details out of use cases."""

from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class AccessTokenService(Protocol):
    """Issue and validate bearer access tokens for authenticated users."""

    def create_access_token(self, user_id: UUID, email: str) -> str:
        """Return a signed access token for ``user_id``."""

        ...

    def parse_user_id(self, token: str) -> UUID:
        """Return the subject user id or raise ``UnauthorizedError``."""

        ...
