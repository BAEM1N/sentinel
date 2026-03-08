"""스케줄러 — 일간/주간/월간 보고서 자동 생성."""

import logging
import os
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger("sentinel.scheduler")


def _generate_scheduled_report(period: str, from_ts: str, to_ts: str):
    """스케줄러에서 호출하는 보고서 생성 함수."""
    from sentinel.services.report_service import ReportService

    auto_html = os.environ.get("SENTINEL_AUTO_HTML", "true").lower() == "true"
    svc = ReportService()

    try:
        result = svc.generate(
            period=period,
            from_ts=from_ts,
            to_ts=to_ts,
            output_html=auto_html,
            notify=True,
        )
        logger.info(
            "[scheduler] %s 보고서 생성 완료: %s | 알림: %s",
            period,
            result.md_path,
            result.notify_results,
        )
    except Exception as e:
        logger.error("[scheduler] %s 보고서 생성 실패: %s", period, e)


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
