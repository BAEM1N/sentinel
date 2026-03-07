"""알림 모듈 — Slack, Telegram, Email(SMTP) 보고서 전송."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

import httpx


def _read_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------

def send_slack(md_path: str, html_path: str | None = None) -> bool:
    """Slack Webhook으로 보고서를 전송합니다."""
    webhook_url = os.environ.get("SENTINEL_SLACK_WEBHOOK")
    if not webhook_url:
        return False

    md_content = _read_file(md_path)
    # Slack은 3000자 제한이므로 요약만 전송
    summary = md_content[:2900] + ("\n..." if len(md_content) > 2900 else "")
    filename = Path(md_path).name

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Sentinel 보고서: {filename}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": summary},
            },
        ],
    }
    resp = httpx.post(webhook_url, json=payload, timeout=15)
    return resp.status_code == 200


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def send_telegram(md_path: str, html_path: str | None = None) -> bool:
    """Telegram Bot으로 보고서를 전송합니다."""
    bot_token = os.environ.get("SENTINEL_TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("SENTINEL_TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return False

    md_content = _read_file(md_path)
    summary = md_content[:4000] + ("\n..." if len(md_content) > 4000 else "")
    filename = Path(md_path).name

    # 텍스트 메시지 전송
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = httpx.post(url, json={
        "chat_id": chat_id,
        "text": f"*Sentinel 보고서: {filename}*\n\n{summary}",
        "parse_mode": "Markdown",
    }, timeout=15)

    # HTML 파일이 있으면 문서로 전송
    if html_path and Path(html_path).exists():
        doc_url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        with open(html_path, "rb") as f:
            httpx.post(doc_url, data={"chat_id": chat_id}, files={"document": f}, timeout=30)

    return resp.status_code == 200


# ---------------------------------------------------------------------------
# Email (SMTP)
# ---------------------------------------------------------------------------

def send_email(md_path: str, html_path: str | None = None) -> bool:
    """SMTP로 보고서를 이메일 전송합니다."""
    smtp_host = os.environ.get("SENTINEL_SMTP_HOST")
    smtp_port = int(os.environ.get("SENTINEL_SMTP_PORT", "587"))
    smtp_user = os.environ.get("SENTINEL_SMTP_USER")
    smtp_pass = os.environ.get("SENTINEL_SMTP_PASS")
    to_addr = os.environ.get("SENTINEL_EMAIL_TO")
    from_addr = os.environ.get("SENTINEL_EMAIL_FROM", smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass, to_addr]):
        return False

    filename = Path(md_path).name
    md_content = _read_file(md_path)

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"Sentinel 보고서: {filename}"
    msg["From"] = from_addr
    msg["To"] = to_addr

    # HTML 본문이 있으면 HTML, 없으면 텍스트
    if html_path and Path(html_path).exists():
        html_content = _read_file(html_path)
        msg.attach(MIMEText(html_content, "html", "utf-8"))
    else:
        msg.attach(MIMEText(md_content, "plain", "utf-8"))

    # MD 파일 첨부
    md_attachment = MIMEBase("application", "octet-stream")
    md_attachment.set_payload(_read_file(md_path).encode("utf-8"))
    encoders.encode_base64(md_attachment)
    md_attachment.add_header("Content-Disposition", f"attachment; filename={filename}")
    msg.attach(md_attachment)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)

    return True


# ---------------------------------------------------------------------------
# 통합 전송
# ---------------------------------------------------------------------------

def send_report(md_path: str, html_path: str | None = None) -> dict[str, bool]:
    """설정된 모든 채널로 보고서를 전송합니다."""
    results = {}
    for name, fn in [("slack", send_slack), ("telegram", send_telegram), ("email", send_email)]:
        try:
            results[name] = fn(md_path, html_path)
        except Exception as e:
            results[name] = False
            print(f"[notify] {name} 전송 실패: {e}")
    return results
