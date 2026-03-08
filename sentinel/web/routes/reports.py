"""보고서 라우트 — 목록, 상세, 발행, 생성."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse

from sentinel.settings import REPORTS_DIR, list_reports

router = APIRouter()


@router.get("/reports", response_class=HTMLResponse)
async def page_reports(request: Request):
    reports = list_reports()
    return request.app.state.templates.TemplateResponse(request, "reports.html", {
        "reports": reports,
        "active_page": "reports",
    })


@router.get("/reports/{filename}", response_class=HTMLResponse)
async def page_report_view(request: Request, filename: str):
    from sentinel.approval import approval_manager

    reports_base = Path(REPORTS_DIR).resolve()
    filepath = (reports_base / filename).resolve()
    if not filepath.is_relative_to(reports_base):
        return HTMLResponse("<h1>Forbidden</h1>", status_code=403)
    if not filepath.exists():
        return HTMLResponse("<h1>Not Found</h1>", status_code=404)

    content = filepath.read_text(encoding="utf-8")
    is_html = filepath.suffix == ".html"

    approval_status = None
    matched_approval = approval_manager.find_by_type_and_param(
        request_type="report_publish",
        param_key="md_path",
        param_value=filename,
    )
    if matched_approval:
        approval_status = matched_approval["status"]

    return request.app.state.templates.TemplateResponse(request, "report_view.html", {
        "filename": filename,
        "content": content,
        "is_html": is_html,
        "active_page": "reports",
        "approval_status": approval_status,
    })


@router.post("/reports/{filename}/publish")
async def action_publish_report(request: Request, filename: str):
    from sentinel.approval import approval_manager, ApprovalStatus
    from sentinel.web.notify import send_report

    matched_item = approval_manager.find_by_type_and_param(
        request_type="report_publish",
        param_key="md_path",
        param_value=filename,
        status_filter=ApprovalStatus.APPROVED.value,
    )
    if not matched_item:
        return HTMLResponse("<h1>승인되지 않은 보고서입니다.</h1>", status_code=403)

    import json as _json
    params = _json.loads(matched_item["params_json"]) if matched_item.get("params_json") else {}
    md_path = params.get("md_path", "")
    html_path = params.get("html_path")
    send_report(md_path, html_path)

    return RedirectResponse(url=f"/reports/{filename}", status_code=303)


@router.get("/reports/{filename}/raw")
async def download_report(filename: str):
    reports_base = Path(REPORTS_DIR).resolve()
    filepath = (reports_base / filename).resolve()
    if not filepath.is_relative_to(reports_base):
        return HTMLResponse("Forbidden", status_code=403)
    if not filepath.exists():
        return HTMLResponse("Not Found", status_code=404)
    media = "text/html" if filepath.suffix == ".html" else "text/markdown"
    return FileResponse(filepath, media_type=media, filename=filename)


@router.post("/api/generate")
async def api_generate(
    request: Request,
    period: str = Form("daily"),
    from_date: str = Form(""),
    to_date: str = Form(""),
    output_html: bool = Form(False),
    require_approval: bool = Form(False),
):
    """보고서 생성 API — 백그라운드 Job으로 실행."""
    if period not in ("daily", "weekly", "monthly"):
        return JSONResponse({"error": f"잘못된 period: {period}"}, status_code=400)

    if from_date:
        try:
            datetime.strptime(from_date, "%Y-%m-%d")
        except ValueError:
            return JSONResponse({"error": "from_date 형식이 잘못됨 (YYYY-MM-DD)"}, status_code=400)

    if to_date:
        try:
            datetime.strptime(to_date, "%Y-%m-%d")
        except ValueError:
            return JSONResponse({"error": "to_date 형식이 잘못됨 (YYYY-MM-DD)"}, status_code=400)

    if from_date and to_date and from_date > to_date:
        return JSONResponse({"error": "from_date가 to_date보다 클 수 없음"}, status_code=400)

    from_ts = f"{from_date}T00:00:00Z" if from_date else ""
    to_ts = f"{to_date}T23:59:59Z" if to_date else ""

    from sentinel.services.job_manager import job_manager
    from sentinel.services.report_service import ReportService

    def _run_report(period, from_ts, to_ts, output_html, require_approval):
        svc = ReportService()
        result = svc.generate(
            period=period,
            from_ts=from_ts,
            to_ts=to_ts,
            output_html=output_html,
            notify=not require_approval,
            require_approval=require_approval,
        )
        return {"md_path": result.md_path, "html_path": result.html_path, "approval_id": result.approval_id}

    job = job_manager.submit(
        "report_generate",
        _run_report,
        params={
            "period": period,
            "from_ts": from_ts,
            "to_ts": to_ts,
            "output_html": output_html,
            "require_approval": require_approval,
        },
    )

    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return RedirectResponse(url=f"/jobs/{job.id}", status_code=303)
    return JSONResponse({"job_id": job.id, "status": job.status.value})
