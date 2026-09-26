"""Outbound notification ports (email summaries, etc.)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmailNotifier(Protocol):
    """Send transactional email to a planner."""

    def send(self, *, to_email: str, subject: str, body_text: str) -> None:
        """Deliver a plain-text email (or log when SMTP is disabled)."""

        ...
