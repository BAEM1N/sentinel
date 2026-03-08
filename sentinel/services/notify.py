"""통합 알림 서비스 — Telegram, Email(SMTP), Slack.

범용 메시지 전송 + 보고서 전송을 모두 지원합니다.
"""

import email.message
import logging
import os
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from email.utils import formataddr
from enum import Enum
from pathlib import Path

import httpx

logger = logging.getLogger("sentinel.notify")


# ---------------------------------------------------------------------------
# 공통 모델
# ---------------------------------------------------------------------------


class Level(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


LEVEL_EMOJI = {
    Level.info: "ℹ️",
    Level.warning: "⚠️",
    Level.critical: "🚨",
}


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------


def send_telegram_message(
    title: str,
    message: str,
    level: Level = Level.info,
    source: str = "",
) -> bool:
    """범용 Telegram 메시지 전송."""
    bot_token = os.environ.get("SENTINEL_TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("SENTINEL_TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return False

    emoji = LEVEL_EMOJI.get(level, "")
    parts = [f"{emoji} <b>{title}</b>"]
    if source:
        parts.append(f"<code>[{source}]</code>")
    parts.append("")
    parts.append(message)
    text = "\n".join(parts)

    resp = httpx.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("ok", False)


def send_telegram_report(md_path: str, html_path: str | None = None) -> bool:
    """보고서 파일을 Telegram으로 전송."""
    bot_token = os.environ.get("SENTINEL_TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("SENTINEL_TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return False

    content = Path(md_path).read_text(encoding="utf-8")
    summary = content[:4000] + ("\n..." if len(content) > 4000 else "")
    filename = Path(md_path).name

    resp = httpx.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": f"*Sentinel 보고서: {filename}*\n\n{summary}",
            "parse_mode": "Markdown",
        },
        timeout=15,
    )

    if html_path and Path(html_path).exists():
        with open(html_path, "rb") as f:
            httpx.post(
                f"https://api.telegram.org/bot{bot_token}/sendDocument",
                data={"chat_id": chat_id},
                files={"document": f},
                timeout=30,
            )

    return resp.status_code == 200


# ---------------------------------------------------------------------------
# Email (SMTP)
# ---------------------------------------------------------------------------


def send_email_message(
    title: str,
    message: str,
    level: Level = Level.info,
    source: str = "",
    to: str = "",
) -> bool:
    """범용 이메일 전송."""
    smtp_host = os.environ.get("SENTINEL_SMTP_HOST")
    smtp_port = int(os.environ.get("SENTINEL_SMTP_PORT", "587"))
    smtp_user = os.environ.get("SENTINEL_SMTP_USER")
    smtp_pass = os.environ.get("SENTINEL_SMTP_PASS")
    from_addr = os.environ.get("SENTINEL_EMAIL_FROM", smtp_user or "")
    to_addr = to or os.environ.get("SENTINEL_EMAIL_TO", "")

    if not all([smtp_host, smtp_user, smtp_pass, to_addr]):
        return False

    emoji = LEVEL_EMOJI.get(level, "")
    msg = email.message.EmailMessage()
    msg["Subject"] = f"{emoji} {title}"
    msg["From"] = formataddr(("Sentinel", from_addr))
    msg["To"] = to_addr

    body_parts = []
    if source:
        body_parts.append(f"[Source: {source}]")
    body_parts.append(message)
    msg.set_content("\n\n".join(body_parts))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
    return True


def send_email_report(md_path: str, html_path: str | None = None) -> bool:
    """보고서 파일을 이메일로 전송."""
    smtp_host = os.environ.get("SENTINEL_SMTP_HOST")
    smtp_port = int(os.environ.get("SENTINEL_SMTP_PORT", "587"))
    smtp_user = os.environ.get("SENTINEL_SMTP_USER")
    smtp_pass = os.environ.get("SENTINEL_SMTP_PASS")
    to_addr = os.environ.get("SENTINEL_EMAIL_TO")
    from_addr = os.environ.get("SENTINEL_EMAIL_FROM", smtp_user or "")

    if not all([smtp_host, smtp_user, smtp_pass, to_addr]):
        return False

    filename = Path(md_path).name
    md_content = Path(md_path).read_text(encoding="utf-8")

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"Sentinel 보고서: {filename}"
    msg["From"] = from_addr
    msg["To"] = to_addr

    if html_path and Path(html_path).exists():
        html_content = Path(html_path).read_text(encoding="utf-8")
        msg.attach(MIMEText(html_content, "html", "utf-8"))
    else:
        msg.attach(MIMEText(md_content, "plain", "utf-8"))

    md_attachment = MIMEBase("application", "octet-stream")
    md_attachment.set_payload(md_content.encode("utf-8"))
    encoders.encode_base64(md_attachment)
    md_attachment.add_header("Content-Disposition", f"attachment; filename={filename}")
    msg.attach(md_attachment)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
    return True


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------


def send_slack_report(md_path: str, html_path: str | None = None) -> bool:
    """Slack Webhook으로 보고서를 전송."""
    webhook_url = os.environ.get("SENTINEL_SLACK_WEBHOOK")
    if not webhook_url:
        return False

    md_content = Path(md_path).read_text(encoding="utf-8")
    summary = md_content[:2900] + ("\n..." if len(md_content) > 2900 else "")
    filename = Path(md_path).name

    resp = httpx.post(webhook_url, json={
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": f"Sentinel 보고서: {filename}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": summary}},
        ],
    }, timeout=15)
    return resp.status_code == 200


# ---------------------------------------------------------------------------
# 통합 전송
# ---------------------------------------------------------------------------


def send_report(md_path: str, html_path: str | None = None) -> dict[str, bool]:
    """설정된 모든 채널로 보고서를 전송합니다."""
    results = {}
    for name, fn in [
        ("slack", send_slack_report),
        ("telegram", send_telegram_report),
        ("email", send_email_report),
    ]:
        try:
            results[name] = fn(md_path, html_path)
        except Exception as e:
            results[name] = False
            logger.warning("%s 전송 실패: %s", name, e)
    return results


def send_notification(
    title: str,
    message: str,
    level: Level = Level.info,
    source: str = "sentinel",
    channel: str = "all",
) -> dict[str, bool]:
    """범용 알림 전송 (telegram, email, 또는 all)."""
    results = {}
    channels = {
        "telegram": send_telegram_message,
        "email": send_email_message,
    }
    targets = channels if channel == "all" else {channel: channels.get(channel)}

    for ch_name, fn in targets.items():
        if fn is None:
            continue
        try:
            results[ch_name] = fn(title=title, message=message, level=level, source=source)
        except Exception as e:
            results[ch_name] = False
            logger.warning("%s 알림 실패: %s", ch_name, e)
    return results
