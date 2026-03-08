"""FastAPI 라우트 — 웹 페이지 + API 엔드포인트."""

import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse

router = APIRouter()
logger = logging.getLogger("sentinel.web")

REPORTS_DIR = os.environ.get("SENTINEL_REPORTS_DIR", "./reports")


def _list_reports() -> list[dict]:
    """reports/ 디렉토리의 보고서 파일 목록을 수정시각 내림차순으로 반환합니다."""
    reports_path = Path(REPORTS_DIR)
    if not reports_path.exists():
        return []

    files = []
    for f in reports_path.iterdir():
        if f.suffix in (".md", ".html"):
            stat = f.stat()
            files.append({
                "name": f.name,
                "type": f.suffix[1:].upper(),
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "modified_ts": stat.st_mtime,
                "period": f.stem.split("_")[0] if "_" in f.stem else "—",
            })
    files.sort(key=lambda x: x["modified_ts"], reverse=True)
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
    filepath = (Path(REPORTS_DIR) / filename).resolve()
    # 경로 탐색 방어 — reports 디렉토리 밖 접근 차단
    if not str(filepath).startswith(str(Path(REPORTS_DIR).resolve())):
        return HTMLResponse("<h1>Forbidden</h1>", status_code=403)
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
    filepath = (Path(REPORTS_DIR) / filename).resolve()
    if not str(filepath).startswith(str(Path(REPORTS_DIR).resolve())):
        return HTMLResponse("Forbidden", status_code=403)
    if not filepath.exists():
        return HTMLResponse("Not Found", status_code=404)
    media = "text/html" if filepath.suffix == ".html" else "text/markdown"
    return FileResponse(filepath, media_type=media, filename=filename)


# ---------------------------------------------------------------------------
# Trace Explorer
# ---------------------------------------------------------------------------

TRACES_PER_PAGE = 20


@router.get("/traces", response_class=HTMLResponse)
async def page_traces(
    request: Request,
    name: str = "",
    user_id: str = "",
    session_id: str = "",
    environment: str = "",
    from_date: str = "",
    to_date: str = "",
    page: int = Query(1, ge=1),
):
    """Trace Explorer 페이지."""
    from sentinel.config import lf_client

    kwargs: dict = {"limit": TRACES_PER_PAGE}
    if name:
        kwargs["name"] = name
    if user_id:
        kwargs["user_id"] = user_id
    if session_id:
        kwargs["session_id"] = session_id
    if environment:
        kwargs["environment"] = environment
    if from_date:
        kwargs["from_timestamp"] = f"{from_date}T00:00:00Z"
    if to_date:
        kwargs["to_timestamp"] = f"{to_date}T23:59:59Z"
    if page > 1:
        kwargs["page"] = page

    traces = []
    total = 0
    has_next = False
    try:
        res = lf_client.api.trace.list(**kwargs)
        data = res.data if hasattr(res, "data") else res
        total_meta = getattr(res, "meta", None)
        if total_meta and hasattr(total_meta, "total_items"):
            total = total_meta.total_items
        else:
            total = len(data)
        for t in data:
            traces.append({
                "id": t.id,
                "name": getattr(t, "name", None),
                "user_id": getattr(t, "user_id", None),
                "session_id": getattr(t, "session_id", None),
                "timestamp": str(getattr(t, "timestamp", ""))[:19],
                "latency": getattr(t, "latency", None),
                "total_cost": getattr(t, "total_cost", None),
                "input_tokens": getattr(t, "input_tokens", None),
                "output_tokens": getattr(t, "output_tokens", None),
                "tags": getattr(t, "tags", []),
                "level": getattr(t, "level", None),
            })
        has_next = len(data) >= TRACES_PER_PAGE
    except Exception:
        logger.exception("Langfuse trace list API 호출 실패")

    filters = {
        "name": name,
        "user_id": user_id,
        "session_id": session_id,
        "environment": environment,
        "from_date": from_date,
        "to_date": to_date,
    }

    return request.app.state.templates.TemplateResponse("traces.html", {
        "request": request,
        "traces": traces,
        "total": total,
        "page": page,
        "has_next": has_next,
        "filters": filters,
        "active_page": "traces",
    })


@router.get("/traces/{trace_id}", response_class=HTMLResponse)
async def page_trace_detail(request: Request, trace_id: str):
    """트레이스 상세 페이지."""
    from sentinel.config import lf_client

    trace: dict = {}
    try:
        t = lf_client.api.trace.get(trace_id)
        trace = {
            "id": t.id,
            "name": getattr(t, "name", None),
            "user_id": getattr(t, "user_id", None),
            "session_id": getattr(t, "session_id", None),
            "input": str(getattr(t, "input", "") or ""),
            "output": str(getattr(t, "output", "") or ""),
            "timestamp": str(getattr(t, "timestamp", "")),
            "latency": getattr(t, "latency", None),
            "total_cost": getattr(t, "total_cost", None),
            "input_tokens": getattr(t, "input_tokens", None),
            "output_tokens": getattr(t, "output_tokens", None),
            "metadata": getattr(t, "metadata", {}),
            "tags": getattr(t, "tags", []),
            "level": getattr(t, "level", None),
            "version": getattr(t, "version", None),
            "environment": getattr(t, "environment", None),
            "release": getattr(t, "release", None),
            "scores": [
                {"name": s.name, "value": s.value, "comment": getattr(s, "comment", "")}
                for s in (getattr(t, "scores", []) or [])
            ],
            "observations": [
                {
                    "id": o.id,
                    "type": getattr(o, "type", None),
                    "name": getattr(o, "name", None),
                    "model": getattr(o, "model", None),
                    "latency": getattr(o, "latency", None),
                    "level": getattr(o, "level", None),
                }
                for o in (getattr(t, "observations", []) or [])
            ],
        }
    except Exception:
        logger.exception("Langfuse trace detail API 호출 실패: %s", trace_id)
        return HTMLResponse("<h1>Trace not found</h1>", status_code=404)

    # 뒤로가기 시 필터 유지를 위한 query string 전달
    back_query = str(request.query_params) if request.query_params else ""

    return request.app.state.templates.TemplateResponse("trace_detail.html", {
        "request": request,
        "trace": trace,
        "back_query": back_query,
        "active_page": "traces",
    })


@router.post("/traces/{trace_id}/evaluate")
async def api_evaluate_trace(request: Request, trace_id: str):
    """트레이스 LLM-as-judge 평가 실행 후 상세 페이지로 리다이렉트."""
    from sentinel.tools.evaluation import evaluate_with_llm

    try:
        evaluate_with_llm.invoke({"trace_id": trace_id})
    except Exception:
        logger.exception("트레이스 평가 실패: %s", trace_id)

    return RedirectResponse(url=f"/traces/{trace_id}", status_code=303)


# ---------------------------------------------------------------------------
# Prompt Registry
# ---------------------------------------------------------------------------


@router.get("/prompts", response_class=HTMLResponse)
async def page_prompts(request: Request):
    """Prompt Registry 목록 페이지."""
    from sentinel.config import lf_client

    prompts = []
    try:
        res = lf_client.api.prompts.list(limit=50)
        data = res.data if hasattr(res, "data") else res
        for p in data:
            prompts.append({
                "name": p.name,
                "version": getattr(p, "version", None),
                "labels": getattr(p, "labels", []),
                "type": getattr(p, "type", "text"),
                "last_updated": str(getattr(p, "last_updated_at", ""))[:19],
            })
    except Exception:
        logger.exception("Langfuse prompts list API 호출 실패")

    return request.app.state.templates.TemplateResponse("prompts.html", {
        "request": request,
        "prompts": prompts,
        "active_page": "prompts",
    })


@router.get("/prompts/{prompt_name}", response_class=HTMLResponse)
async def page_prompt_detail(request: Request, prompt_name: str, version: int = 0):
    """프롬프트 상세 페이지."""
    from sentinel.config import lf_client

    prompt_data = {}
    versions = []
    try:
        # 현재 버전 조회
        if version > 0:
            p = lf_client.get_prompt(prompt_name, version=version, type="text")
        else:
            p = lf_client.get_prompt(prompt_name, type="text")

        prompt_data = {
            "name": p.name,
            "version": getattr(p, "version", None),
            "prompt": p.prompt,
            "labels": getattr(p, "labels", []),
            "type": getattr(p, "type", "text"),
        }

        # 버전 목록 (Langfuse API)
        try:
            versions_res = lf_client.api.prompts.list(name=prompt_name, limit=50)
            vdata = versions_res.data if hasattr(versions_res, "data") else versions_res
            for v in vdata:
                versions.append({
                    "version": getattr(v, "version", None),
                    "labels": getattr(v, "labels", []),
                    "created_at": str(getattr(v, "created_at", ""))[:19],
                })
        except Exception:
            pass

    except Exception:
        logger.exception("프롬프트 조회 실패: %s", prompt_name)
        return HTMLResponse("<h1>Prompt not found</h1>", status_code=404)

    return request.app.state.templates.TemplateResponse("prompt_detail.html", {
        "request": request,
        "prompt": prompt_data,
        "versions": versions,
        "active_page": "prompts",
    })


@router.get("/prompts/{prompt_name}/compare", response_class=HTMLResponse)
async def page_prompt_compare(request: Request, prompt_name: str, v1: int = 0, v2: int = 0):
    """프롬프트 버전 비교."""
    from sentinel.config import lf_client

    left = right = None
    try:
        if v1 > 0:
            p1 = lf_client.get_prompt(prompt_name, version=v1, type="text")
            left = {"version": v1, "prompt": p1.prompt, "labels": getattr(p1, "labels", [])}
        if v2 > 0:
            p2 = lf_client.get_prompt(prompt_name, version=v2, type="text")
            right = {"version": v2, "prompt": p2.prompt, "labels": getattr(p2, "labels", [])}
    except Exception:
        logger.exception("프롬프트 비교 조회 실패: %s", prompt_name)

    return request.app.state.templates.TemplateResponse("prompt_compare.html", {
        "request": request,
        "prompt_name": prompt_name,
        "left": left,
        "right": right,
        "v1": v1,
        "v2": v2,
        "active_page": "prompts",
    })


# ---------------------------------------------------------------------------
# API 엔드포인트
# ---------------------------------------------------------------------------

@router.post("/api/generate")
async def api_generate(
    request: Request,
    period: str = Form("daily"),
    from_date: str = Form(""),
    to_date: str = Form(""),
    output_html: bool = Form(False),
):
    """보고서 생성 API — 백그라운드 Job으로 실행."""
    # --- 입력 검증 ---
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

    # 날짜 → ISO8601 변환
    from_ts = f"{from_date}T00:00:00Z" if from_date else ""
    to_ts = f"{to_date}T23:59:59Z" if to_date else ""

    from sentinel.services.job_manager import job_manager
    from sentinel.services.report_service import ReportService

    def _run_report(period, from_ts, to_ts, output_html):
        svc = ReportService()
        result = svc.generate(
            period=period,
            from_ts=from_ts,
            to_ts=to_ts,
            output_html=output_html,
            notify=True,
        )
        return {"md_path": result.md_path, "html_path": result.html_path}

    job = job_manager.submit(
        "report_generate",
        _run_report,
        params={
            "period": period,
            "from_ts": from_ts,
            "to_ts": to_ts,
            "output_html": output_html,
        },
    )

    # 브라우저 요청이면 jobs 페이지로 리다이렉트, API 요청이면 JSON 반환
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return RedirectResponse(url=f"/jobs/{job.id}", status_code=303)
    return JSONResponse({"job_id": job.id, "status": job.status.value})


# ---------------------------------------------------------------------------
# Background Jobs
# ---------------------------------------------------------------------------


@router.get("/jobs", response_class=HTMLResponse)
async def page_jobs(request: Request):
    """Job 목록 페이지."""
    from sentinel.services.job_manager import job_manager

    jobs = [j.to_dict() for j in job_manager.list_jobs(limit=50)]
    return request.app.state.templates.TemplateResponse("jobs.html", {
        "request": request,
        "jobs": jobs,
        "active_page": "jobs",
    })


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def page_job_detail(request: Request, job_id: str):
    """Job 상세 페이지."""
    from sentinel.services.job_manager import job_manager

    job = job_manager.get(job_id)
    if not job:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)
    return request.app.state.templates.TemplateResponse("job_detail.html", {
        "request": request,
        "job": job.to_dict(),
        "active_page": "jobs",
    })


@router.get("/api/jobs/{job_id}")
async def api_job_status(job_id: str):
    """Job 상태 JSON API (폴링용)."""
    from sentinel.services.job_manager import job_manager

    job = job_manager.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return JSONResponse(job.to_dict())


@router.get("/audit", response_class=HTMLResponse)
async def page_audit(request: Request, limit: int = 50, run_id: str = ""):
    """감사 로그 페이지."""
    from sentinel.audit import audit_log
    logs = audit_log.query(limit=limit, run_id=run_id or None)
    return request.app.state.templates.TemplateResponse("audit.html", {
        "request": request,
        "logs": logs,
        "active_page": "audit",
    })


@router.get("/scheduler", response_class=HTMLResponse)
async def page_scheduler(request: Request):
    """스케줄러 페이지."""
    scheduler = getattr(request.app.state, "scheduler", None)
    tz_label = os.environ.get("SENTINEL_TIMEZONE", "UTC")
    desc_map = {
        "daily_report": f"Every day at 00:00 ({tz_label})",
        "weekly_report": f"Every Monday at 00:00 ({tz_label})",
        "monthly_report": f"1st of each month at 00:00 ({tz_label})",
    }
    jobs = []
    running = False
    if scheduler is not None:
        running = scheduler.running
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "description": desc_map.get(job.id, str(job.trigger)),
                "next_run": str(job.next_run_time)[:19] if job.next_run_time else "paused",
            })
    return request.app.state.templates.TemplateResponse("scheduler.html", {
        "request": request,
        "running": running,
        "jobs": jobs,
        "active_page": "scheduler",
    })


@router.get("/api/scheduler/status")
async def scheduler_status(request: Request):
    """스케줄러 상태 JSON API."""
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        return {"running": False, "jobs": [], "note": "scheduler disabled"}
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": str(job.next_run_time) if job.next_run_time else "paused",
            "trigger": str(job.trigger),
        })
    return {"running": scheduler.running, "jobs": jobs}


# ---------------------------------------------------------------------------
# Health / Ready 엔드포인트
# ---------------------------------------------------------------------------

@router.get("/health")
async def health():
    """프로세스 헬스 체크."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}


@router.get("/ready")
async def readiness(request: Request):
    """의존 서비스 준비 상태 체크."""
    checks: dict[str, str] = {}

    # Langfuse 연결
    try:
        from sentinel.config import lf_client
        lf_client.api.trace.list(limit=1)
        checks["langfuse"] = "ok"
    except Exception as e:
        checks["langfuse"] = f"error: {e}"

    # 스토리지
    reports_path = Path(REPORTS_DIR)
    if reports_path.exists() and os.access(reports_path, os.W_OK):
        checks["storage"] = "ok"
    else:
        checks["storage"] = "error: reports dir not writable"

    # 스케줄러
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        checks["scheduler"] = "disabled"
    elif scheduler.running:
        checks["scheduler"] = "ok"
    else:
        checks["scheduler"] = "stopped"

    ready = all(v == "ok" for k, v in checks.items() if k != "scheduler")
    status_code = 200 if ready else 503
    return JSONResponse(
        {"ready": ready, "checks": checks},
        status_code=status_code,
    )
