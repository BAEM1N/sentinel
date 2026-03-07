"""FastAPI 라우트 — 웹 페이지 + API 엔드포인트."""

import os
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse

router = APIRouter()

REPORTS_DIR = os.environ.get("SENTINEL_REPORTS_DIR", "./reports")


def _list_reports() -> list[dict]:
    """reports/ 디렉토리의 보고서 파일 목록을 반환합니다."""
    reports_path = Path(REPORTS_DIR)
    if not reports_path.exists():
        return []

    files = []
    for f in sorted(reports_path.iterdir(), reverse=True):
        if f.suffix in (".md", ".html"):
            stat = f.stat()
            files.append({
                "name": f.name,
                "type": f.suffix[1:].upper(),
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "period": f.stem.split("_")[0] if "_" in f.stem else "—",
            })
    return files


# ---------------------------------------------------------------------------
# 페이지 라우트
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def page_index(request: Request):
    """대시보드 페이지."""
    reports = _list_reports()
    md_count = sum(1 for r in reports if r["type"] == "MD")
    html_count = sum(1 for r in reports if r["type"] == "HTML")
    return request.app.state.templates.TemplateResponse("index.html", {
        "request": request,
        "reports": reports[:10],
        "md_count": md_count,
        "html_count": html_count,
        "total": len(reports),
        "active_page": "dashboard",
    })


@router.get("/reports", response_class=HTMLResponse)
async def page_reports(request: Request):
    """보고서 목록 페이지."""
    reports = _list_reports()
    return request.app.state.templates.TemplateResponse("reports.html", {
        "request": request,
        "reports": reports,
        "active_page": "reports",
    })


@router.get("/reports/{filename}", response_class=HTMLResponse)
async def page_report_view(request: Request, filename: str):
    """보고서 상세 보기."""
    filepath = Path(REPORTS_DIR) / filename
    if not filepath.exists():
        return HTMLResponse("<h1>Not Found</h1>", status_code=404)

    content = filepath.read_text(encoding="utf-8")
    is_html = filepath.suffix == ".html"

    return request.app.state.templates.TemplateResponse("report_view.html", {
        "request": request,
        "filename": filename,
        "content": content,
        "is_html": is_html,
        "active_page": "reports",
    })


@router.get("/reports/{filename}/raw")
async def download_report(filename: str):
    """보고서 파일 다운로드."""
    filepath = Path(REPORTS_DIR) / filename
    if not filepath.exists():
        return HTMLResponse("Not Found", status_code=404)
    media = "text/html" if filepath.suffix == ".html" else "text/markdown"
    return FileResponse(filepath, media_type=media, filename=filename)


# ---------------------------------------------------------------------------
# API 엔드포인트
# ---------------------------------------------------------------------------

@router.post("/api/generate")
async def api_generate(
    period: str = Form("daily"),
    from_date: str = Form(""),
    to_date: str = Form(""),
    output_html: bool = Form(False),
):
    """보고서 생성 API."""
    from sentinel.tools.metrics import (
        _collect_report_data, _load_template, _strip_code_fence,
        REPORT_MD_PROMPT, REPORT_HTML_PROMPT,
    )
    from sentinel.config import model as llm

    now = datetime.utcnow()
    if not to_date:
        to_ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        to_ts = f"{to_date}T23:59:59Z"

    if not from_date:
        delta = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 1)
        from_ts = (now - timedelta(days=delta)).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        from_ts = f"{from_date}T00:00:00Z"

    gran = {"daily": "hour", "weekly": "day", "monthly": "week"}.get(period, "day")
    period_kr = {"daily": "일간", "weekly": "주간", "monthly": "월간"}.get(period, period)
    date_label = f"{from_ts[:10]} ~ {to_ts[:10]}"
    generated_at = now.strftime("%Y-%m-%d %H:%M UTC")

    metrics_json, traces_json, scores_json = _collect_report_data(from_ts, to_ts, gran)

    reports_dir = os.environ.get("SENTINEL_REPORTS_DIR", "./reports")
    os.makedirs(reports_dir, exist_ok=True)

    # MD
    md_prompt = REPORT_MD_PROMPT.format(
        period_kr=period_kr, from_ts=from_ts, to_ts=to_ts,
        date_label=date_label, generated_at=generated_at,
        metrics_json=metrics_json, traces_json=traces_json,
        scores_json=scores_json,
    )
    md_resp = llm.invoke(md_prompt)
    md_content = _strip_code_fence(md_resp.content)
    md_path = os.path.join(reports_dir, f"{period}_report_{from_ts[:10]}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # HTML (옵션)
    if output_html:
        html_prompt = REPORT_HTML_PROMPT.format(
            period_kr=period_kr, from_ts=from_ts, to_ts=to_ts,
            date_label=date_label, generated_at=generated_at,
            metrics_json=metrics_json, traces_json=traces_json,
            scores_json=scores_json,
        )
        html_resp = llm.invoke(html_prompt)
        html_body = _strip_code_fence(html_resp.content)
        template = _load_template()
        title = f"LLMOps {period_kr} 보고서 — {date_label}"
        full_html = (
            template
            .replace("{{title}}", title)
            .replace("{{content}}", html_body)
            .replace("{{generated_at}}", generated_at)
        )
        html_path = os.path.join(reports_dir, f"{period}_report_{from_ts[:10]}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(full_html)

    # 알림 전송
    from sentinel.web.notify import send_report
    html_file = os.path.join(reports_dir, f"{period}_report_{from_ts[:10]}.html") if output_html else None
    send_report(md_path, html_file)

    return RedirectResponse(url="/reports", status_code=303)


@router.get("/scheduler", response_class=HTMLResponse)
async def page_scheduler(request: Request):
    """스케줄러 페이지."""
    scheduler = request.app.state.scheduler
    desc_map = {
        "daily_report": "Every day at 00:00",
        "weekly_report": "Every Monday at 00:00",
        "monthly_report": "1st of each month at 00:00",
    }
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "description": desc_map.get(job.id, str(job.trigger)),
            "next_run": str(job.next_run_time)[:19] if job.next_run_time else "paused",
        })
    return request.app.state.templates.TemplateResponse("scheduler.html", {
        "request": request,
        "running": scheduler.running,
        "jobs": jobs,
        "active_page": "scheduler",
    })


@router.get("/api/scheduler/status")
async def scheduler_status(request: Request):
    """스케줄러 상태 JSON API."""
    scheduler = request.app.state.scheduler
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": str(job.next_run_time) if job.next_run_time else "paused",
            "trigger": str(job.trigger),
        })
    return {"running": scheduler.running, "jobs": jobs}
