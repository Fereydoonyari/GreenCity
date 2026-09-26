"""Outbound notification adapters."""

from greencity.infrastructure.notifications.email import build_email_notifier

__all__ = ["build_email_notifier"]
