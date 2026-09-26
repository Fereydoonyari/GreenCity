"""SMTP / logging email notifier and analysis-summary templates."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from greencity.config import Settings, get_settings

logger = logging.getLogger(__name__)


def render_analysis_summary_email(
    *,
    recipient_name: str,
    project_name: str,
    aoi_name: str,
    aoi_kind: str,
    executive_summary: str,
    priority_band: str | None = None,
    score: float | None = None,
) -> tuple[str, str]:
    """Return ``(subject, plain_text_body)`` for a completed analysis."""

    kind_label = "city-wide" if aoi_kind == "city" else "neighborhood"
    subject = f"GreenCity AI — {kind_label} summary for {aoi_name}"
    score_line = ""
    if score is not None and priority_band:
        score_line = f"\nGreen deficiency score: {score:.1f} ({priority_band} priority)\n"
    body = (
        f"Hello {recipient_name},\n\n"
        f"Your GreenCity AI analysis for project “{project_name}” is ready.\n\n"
        f"Area: {aoi_name} ({kind_label})\n"
        f"{score_line}\n"
        f"Summary\n"
        f"-------\n"
        f"{executive_summary.strip()}\n\n"
        f"— GreenCity AI\n"
        f"(This is an automated template summary; a richer agent narrative will follow later.)\n"
    )
    return subject, body


def render_comparison_summary_email(
    *,
    recipient_name: str,
    project_name: str,
    city_name: str | None,
    ranking_lines: list[str],
    notes: str = "",
) -> tuple[str, str]:
    """Return ``(subject, plain_text_body)`` for a neighborhood comparison digest."""

    subject = f"GreenCity AI — neighborhood comparison for {project_name}"
    city_line = f"City study area: {city_name}\n" if city_name else ""
    rankings = "\n".join(ranking_lines) if ranking_lines else "(no neighborhoods ranked yet)"
    notes_block = f"\nNotes\n-----\n{notes.strip()}\n" if notes.strip() else ""
    body = (
        f"Hello {recipient_name},\n\n"
        f"Your neighborhood comparison for project “{project_name}” is ready.\n\n"
        f"{city_line}"
        f"Ranked neighborhoods (highest green-deficiency priority first):\n"
        f"{rankings}\n"
        f"{notes_block}\n"
        f"— GreenCity AI\n"
        f"(Template email — fuller agent write-up coming later.)\n"
    )
    return subject, body


class LoggingEmailNotifier:
    """Development notifier that logs the message instead of sending SMTP."""

    def send(self, *, to_email: str, subject: str, body_text: str) -> None:
        logger.info(
            "email_stub to=%s subject=%s\n%s",
            to_email,
            subject,
            body_text,
        )


class SmtpEmailNotifier:
    """Send plain-text email via SMTP when configured."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, *, to_email: str, subject: str, body_text: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._settings.smtp_from
        message["To"] = to_email
        message.set_content(body_text)

        with smtplib.SMTP(
            self._settings.smtp_host,
            self._settings.smtp_port,
            timeout=30,
        ) as client:
            if self._settings.smtp_use_tls:
                client.starttls()
            user = self._settings.smtp_username.strip()
            if user:
                client.login(user, self._settings.smtp_password)
            client.send_message(message)


def build_email_notifier(settings: Settings | None = None) -> LoggingEmailNotifier | SmtpEmailNotifier:
    """Return SMTP notifier when enabled and host is set; otherwise log stub."""

    cfg = settings or get_settings()
    if cfg.email_enabled and cfg.smtp_host.strip():
        return SmtpEmailNotifier(cfg)
    return LoggingEmailNotifier()
