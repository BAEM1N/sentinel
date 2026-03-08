"""보고서 생성 통합 서비스.

기존 3곳(metrics.py generate_report, routes.py api_generate, scheduler.py
_generate_scheduled_report)에 분산되어 있던 보고서 생성 로직을 하나로 통합합니다.
"""

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("sentinel.services.report")


@dataclass
class ReportResult:
    """보고서 생성 결과."""

    md_path: str
    html_path: str | None
    period: str
    from_ts: str
    to_ts: str
    run_id: str
    notify_results: dict | None = None


class ReportService:
    """보고서 생성 통합 서비스."""

    # period → granularity 매핑
    _GRAN_MAP = {"daily": "hour", "weekly": "day", "monthly": "week"}
    # period → 한국어 레이블
    _PERIOD_KR_MAP = {"daily": "일간", "weekly": "주간", "monthly": "월간"}
    # period → 기본 날짜 범위(일)
    _DELTA_MAP = {"daily": 1, "weekly": 7, "monthly": 30}

    def __init__(
        self,
        reports_dir: str | None = None,
        model=None,
        auto_html: bool | None = None,
    ):
        self.reports_dir = reports_dir or os.environ.get(
            "SENTINEL_REPORTS_DIR", "./reports"
        )
        if model is not None:
            self._model = model
        else:
            from sentinel.config import model as default_model

            self._model = default_model

        self.auto_html = auto_html

    # ------------------------------------------------------------------
    # 핵심 메서드
    # ------------------------------------------------------------------

    def generate(
        self,
        period: str = "daily",
        from_ts: str = "",
        to_ts: str = "",
        output_html: bool = False,
        notify: bool = False,
    ) -> ReportResult:
        """보고서 생성 + 저장 + (옵션) 알림.

        Args:
            period: 보고서 주기 (daily, weekly, monthly)
            from_ts: 시작 날짜 (ISO8601, 비우면 자동 계산)
            to_ts: 종료 날짜 (ISO8601, 비우면 현재)
            output_html: True이면 HTML 보고서도 추가 생성
            notify: True이면 알림 채널로 전송

        Returns:
            ReportResult 인스턴스
        """
        from sentinel.tools.metrics import (
            REPORT_HTML_PROMPT,
            REPORT_MD_PROMPT,
            _collect_report_data,
            _load_template,
            _strip_code_fence,
        )

        # 1. 날짜 기본값 계산 -------------------------------------------------
        now = datetime.now(timezone.utc)
        if not to_ts:
            to_ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        if not from_ts:
            delta = self._DELTA_MAP.get(period, 1)
            from_ts = (now - timedelta(days=delta)).strftime("%Y-%m-%dT%H:%M:%SZ")

        gran = self._GRAN_MAP.get(period, "day")
        period_kr = self._PERIOD_KR_MAP.get(period, period)
        date_label = f"{from_ts[:10]} ~ {to_ts[:10]}"
        generated_at = now.strftime("%Y-%m-%d %H:%M UTC")
        run_id = uuid.uuid4().hex[:8]

        # 2. 데이터 수집 -------------------------------------------------------
        metrics_json, traces_json, scores_json = _collect_report_data(
            from_ts, to_ts, gran
        )

        # 3. 파일 준비 ---------------------------------------------------------
        os.makedirs(self.reports_dir, exist_ok=True)
        file_stem = f"{period}_report_{from_ts[:10]}_{run_id}"

        fmt_kwargs = dict(
            period_kr=period_kr,
            from_ts=from_ts,
            to_ts=to_ts,
            date_label=date_label,
            generated_at=generated_at,
            metrics_json=metrics_json,
            traces_json=traces_json,
            scores_json=scores_json,
        )

        # 4. Markdown 보고서 (항상 생성) ----------------------------------------
        md_prompt = REPORT_MD_PROMPT.format(**fmt_kwargs)
        md_resp = self._model.invoke(md_prompt)
        md_content = _strip_code_fence(md_resp.content)

        md_path = os.path.join(self.reports_dir, f"{file_stem}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # 5. HTML 보고서 (옵션) -------------------------------------------------
        html_path: str | None = None
        if output_html:
            html_prompt = REPORT_HTML_PROMPT.format(**fmt_kwargs)
            html_resp = self._model.invoke(html_prompt)
            html_body = _strip_code_fence(html_resp.content)

            template = _load_template()
            title = f"LLMOps {period_kr} 보고서 — {date_label}"
            full_html = (
                template.replace("{{title}}", title)
                .replace("{{content}}", html_body)
                .replace("{{generated_at}}", generated_at)
            )

            html_path = os.path.join(self.reports_dir, f"{file_stem}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(full_html)

        # 6. 알림 전송 (옵션) ---------------------------------------------------
        notify_results: dict | None = None
        if notify:
            from sentinel.web.notify import send_report

            notify_results = send_report(md_path, html_path)

        return ReportResult(
            md_path=md_path,
            html_path=html_path,
            period=period,
            from_ts=from_ts,
            to_ts=to_ts,
            run_id=run_id,
            notify_results=notify_results,
        )
