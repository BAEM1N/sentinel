"""스케줄러 — 일간/주간/월간 보고서 자동 생성."""

import logging
import os
import uuid
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from sentinel.tools.metrics import _collect_report_data, _load_template, _strip_code_fence
from sentinel.tools.metrics import REPORT_MD_PROMPT, REPORT_HTML_PROMPT
from sentinel.config import model
from sentinel.web.notify import send_report

logger = logging.getLogger("sentinel.scheduler")


def _generate_scheduled_report(period: str, from_ts: str, to_ts: str):
    """스케줄러에서 호출하는 보고서 생성 함수."""
    gran = {"daily": "hour", "weekly": "day", "monthly": "week"}.get(period, "day")
    period_kr = {"daily": "일간", "weekly": "주간", "monthly": "월간"}.get(period, period)
    date_label = f"{from_ts[:10]} ~ {to_ts[:10]}"
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    run_id = uuid.uuid4().hex[:8]

    try:
        metrics_json, traces_json, scores_json = _collect_report_data(from_ts, to_ts, gran)
    except Exception as e:
        logger.error("[scheduler] %s 보고서 데이터 수집 실패: %s", period, e)
        return

    reports_dir = os.environ.get("SENTINEL_REPORTS_DIR", "./reports")
    os.makedirs(reports_dir, exist_ok=True)

    file_stem = f"{period}_report_{from_ts[:10]}_{run_id}"

    # MD 보고서
    md_prompt = REPORT_MD_PROMPT.format(
        period_kr=period_kr, from_ts=from_ts, to_ts=to_ts,
        date_label=date_label, generated_at=generated_at,
        metrics_json=metrics_json, traces_json=traces_json,
        scores_json=scores_json,
    )
    try:
        md_resp = model.invoke(md_prompt)
    except Exception as e:
        logger.error("[scheduler] %s MD 보고서 LLM 호출 실패: %s", period, e)
        return
    md_content = _strip_code_fence(md_resp.content)
    md_path = os.path.join(reports_dir, f"{file_stem}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # HTML 보고서 (스케줄러는 환경변수 기반)
    html_path = None
    auto_html = os.environ.get("SENTINEL_AUTO_HTML", "true").lower() == "true"
    if auto_html:
        html_prompt = REPORT_HTML_PROMPT.format(
            period_kr=period_kr, from_ts=from_ts, to_ts=to_ts,
            date_label=date_label, generated_at=generated_at,
            metrics_json=metrics_json, traces_json=traces_json,
            scores_json=scores_json,
        )
        try:
            html_resp = model.invoke(html_prompt)
        except Exception as e:
            logger.error("[scheduler] %s HTML 보고서 LLM 호출 실패: %s", period, e)
            # MD는 이미 저장됐으므로 알림은 MD만으로 진행
            results = send_report(md_path, None)
            logger.info("[scheduler] %s 보고서 생성 (MD만): %s | 알림: %s", period, md_path, results)
            return
        html_body = _strip_code_fence(html_resp.content)
        template = _load_template()
        title = f"LLMOps {period_kr} 보고서 — {date_label}"
        full_html = (
            template
            .replace("{{title}}", title)
            .replace("{{content}}", html_body)
            .replace("{{generated_at}}", generated_at)
        )
        html_path = os.path.join(reports_dir, f"{file_stem}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(full_html)

    # 알림 전송
    results = send_report(md_path, html_path)
    logger.info("[scheduler] %s 보고서 생성 완료: %s | 알림: %s", period, md_path, results)


def _job_daily():
    """매일 00:00 — 전일 보고서."""
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    from_ts = yesterday.strftime("%Y-%m-%dT00:00:00Z")
    to_ts = yesterday.strftime("%Y-%m-%dT23:59:59Z")
    _generate_scheduled_report("daily", from_ts, to_ts)


def _job_weekly():
    """매주 월요일 00:00 — 지난주 월~일 보고서."""
    now = datetime.utcnow()
    last_monday = now - timedelta(days=now.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    from_ts = last_monday.strftime("%Y-%m-%dT00:00:00Z")
    to_ts = last_sunday.strftime("%Y-%m-%dT23:59:59Z")
    _generate_scheduled_report("weekly", from_ts, to_ts)


def _job_monthly():
    """매월 1일 00:00 — 지난달 보고서."""
    now = datetime.utcnow()
    first_of_this_month = now.replace(day=1)
    last_day_prev = first_of_this_month - timedelta(days=1)
    first_of_prev = last_day_prev.replace(day=1)
    from_ts = first_of_prev.strftime("%Y-%m-%dT00:00:00Z")
    to_ts = last_day_prev.strftime("%Y-%m-%dT23:59:59Z")
    _generate_scheduled_report("monthly", from_ts, to_ts)


def create_scheduler() -> AsyncIOScheduler:
    """APScheduler를 생성하고 크론 잡을 등록합니다."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(_job_daily, "cron", hour=0, minute=0, id="daily_report")
    scheduler.add_job(_job_weekly, "cron", day_of_week="mon", hour=0, minute=0, id="weekly_report")
    scheduler.add_job(_job_monthly, "cron", day=1, hour=0, minute=0, id="monthly_report")
    return scheduler
