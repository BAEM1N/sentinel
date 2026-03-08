"""FastAPI 라우트 — 웹 페이지 + API 엔드포인트."""

import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

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
    import json
    from sentinel.approval import approval_manager

    reports_base = Path(REPORTS_DIR).resolve()
    filepath = (reports_base / filename).resolve()
    # 경로 탐색 방어 — reports 디렉토리 밖 접근 차단
    if not filepath.is_relative_to(reports_base):
        return HTMLResponse("<h1>Forbidden</h1>", status_code=403)
    if not filepath.exists():
        return HTMLResponse("<h1>Not Found</h1>", status_code=404)

    content = filepath.read_text(encoding="utf-8")
    is_html = filepath.suffix == ".html"

    # 이 보고서에 대한 승인 상태 확인
    approval_status = None
    all_approvals = approval_manager.list_all(limit=500)
    for item in all_approvals:
        if item.get("request_type") != "report_publish":
            continue
        params = json.loads(item["params_json"]) if item.get("params_json") else {}
        md_basename = os.path.basename(params.get("md_path", ""))
        html_basename = os.path.basename(params.get("html_path", "")) if params.get("html_path") else ""
        if md_basename == filename or html_basename == filename:
            approval_status = item["status"]
            break

    return request.app.state.templates.TemplateResponse("report_view.html", {
        "request": request,
        "filename": filename,
        "content": content,
        "is_html": is_html,
        "active_page": "reports",
        "approval_status": approval_status,
    })


@router.post("/reports/{filename}/publish")
async def action_publish_report(request: Request, filename: str):
    """승인된 보고서를 발행(알림 전송)합니다."""
    import json
    from sentinel.approval import approval_manager, ApprovalStatus

    # 해당 보고서에 대한 승인 요청 검색
    all_items = approval_manager.list_all(limit=500, status_filter=ApprovalStatus.APPROVED.value)
    matched = None
    for item in all_items:
        if item.get("request_type") != "report_publish":
            continue
        params = json.loads(item["params_json"]) if item.get("params_json") else {}
        md_basename = os.path.basename(params.get("md_path", ""))
        html_basename = os.path.basename(params.get("html_path", "")) if params.get("html_path") else ""
        if md_basename == filename or html_basename == filename:
            matched = params
            break

    if not matched:
        return HTMLResponse("<h1>승인되지 않은 보고서입니다.</h1>", status_code=403)

    # 승인 확인 → 알림 전송
    from sentinel.web.notify import send_report

    md_path = matched.get("md_path", "")
    html_path = matched.get("html_path")
    send_report(md_path, html_path)

    return RedirectResponse(url=f"/reports/{filename}", status_code=303)


@router.get("/reports/{filename}/raw")
async def download_report(filename: str):
    """보고서 파일 다운로드."""
    reports_base = Path(REPORTS_DIR).resolve()
    filepath = (reports_base / filename).resolve()
    if not filepath.is_relative_to(reports_base):
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
    api_error = ""
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
    except Exception as e:
        logger.exception("Langfuse trace list API 호출 실패")
        api_error = f"Langfuse API 오류: {e}"

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
        "api_error": api_error,
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
    api_error = ""
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
    except Exception as e:
        logger.exception("Langfuse prompts list API 호출 실패")
        api_error = f"Langfuse API 오류: {e}"

    return request.app.state.templates.TemplateResponse("prompts.html", {
        "request": request,
        "prompts": prompts,
        "active_page": "prompts",
        "api_error": api_error,
    })


@router.get("/prompts/{prompt_name}", response_class=HTMLResponse)
async def page_prompt_detail(request: Request, prompt_name: str, version: int = 0):
    """프롬프트 상세 페이지."""
    from sentinel.config import lf_client

    prompt_name = unquote(prompt_name)

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

    prompt_name = unquote(prompt_name)
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
    require_approval: bool = Form(False),
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


# ---------------------------------------------------------------------------
# Approvals (HITL)
# ---------------------------------------------------------------------------


@router.get("/approvals", response_class=HTMLResponse)
async def page_approvals(request: Request):
    """HITL 승인 관리 페이지."""
    from sentinel.approval import approval_manager, ApprovalStatus

    pending = approval_manager.get_pending()
    all_items = approval_manager.list_all(limit=200)
    approved_count = sum(1 for a in all_items if a["status"] == ApprovalStatus.APPROVED.value)
    rejected_count = sum(1 for a in all_items if a["status"] == ApprovalStatus.REJECTED.value)
    history = [a for a in all_items if a["status"] != ApprovalStatus.PENDING.value]

    return request.app.state.templates.TemplateResponse("approvals.html", {
        "request": request,
        "pending": pending,
        "history": history,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "active_page": "approvals",
    })


@router.post("/approvals/{approval_id}/approve")
async def action_approve(approval_id: str, decided_by: str = Form(""), reason: str = Form("")):
    """승인 처리 후 목록 페이지로 리다이렉트."""
    from sentinel.approval import approval_manager

    approval_manager.approve(approval_id, decided_by=decided_by, reason=reason)
    return RedirectResponse(url="/approvals", status_code=303)


@router.post("/approvals/{approval_id}/reject")
async def action_reject(approval_id: str, decided_by: str = Form(""), reason: str = Form("")):
    """거절 처리 후 목록 페이지로 리다이렉트."""
    from sentinel.approval import approval_manager

    approval_manager.reject(approval_id, decided_by=decided_by, reason=reason)
    return RedirectResponse(url="/approvals", status_code=303)


@router.get("/api/approvals/pending")
async def api_approvals_pending():
    """대기 중인 승인 요청 JSON API (에이전트 폴링용)."""
    from sentinel.approval import approval_manager

    pending = approval_manager.get_pending()
    return JSONResponse({"pending": pending, "count": len(pending)})


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


# ---------------------------------------------------------------------------
# Eval Dashboard
# ---------------------------------------------------------------------------


@router.get("/eval", response_class=HTMLResponse)
async def page_eval(request: Request):
    """Eval Dashboard — 스코어 데이터 집계 페이지."""
    from sentinel.config import lf_client

    score_groups: dict[str, list] = defaultdict(list)
    api_error = ""
    try:
        res = lf_client.api.score_v_2.get(limit=200)
        data = res.data if hasattr(res, "data") else res
        for s in data:
            name = getattr(s, "name", None) or "unknown"
            score_groups[name].append({
                "value": getattr(s, "value", None),
                "trace_id": getattr(s, "trace_id", None),
                "timestamp": str(getattr(s, "timestamp", ""))[:19],
                "comment": getattr(s, "comment", None),
            })
    except Exception as e:
        logger.exception("Langfuse score API 호출 실패")
        api_error = f"Langfuse API 오류: {e}"

    # 통계 계산
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    total_count = 0
    all_values = []
    score_cards = []

    for name, scores in sorted(score_groups.items()):
        values = [s["value"] for s in scores if s["value"] is not None]
        total_count += len(scores)
        all_values.extend(values)

        avg_val = sum(values) / len(values) if values else 0
        min_val = min(values) if values else 0
        max_val = max(values) if values else 0

        # 최근 7일 트렌드 (날짜별 평균)
        trend: dict[str, list[float]] = defaultdict(list)
        for s in scores:
            if s["value"] is not None and s["timestamp"]:
                try:
                    ts = datetime.fromisoformat(s["timestamp"].replace("Z", "+00:00"))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts >= seven_days_ago:
                        day_key = ts.strftime("%m-%d")
                        trend[day_key].append(s["value"])
                except (ValueError, TypeError):
                    pass

        trend_data = []
        for day_key in sorted(trend.keys()):
            day_vals = trend[day_key]
            trend_data.append({
                "day": day_key,
                "avg": sum(day_vals) / len(day_vals),
                "count": len(day_vals),
            })

        score_cards.append({
            "name": name,
            "count": len(scores),
            "avg": round(avg_val, 3),
            "min": round(min_val, 3),
            "max": round(max_val, 3),
            "trend": trend_data,
            "recent": scores[:10],
        })

    overall_avg = round(sum(all_values) / len(all_values), 3) if all_values else 0

    return request.app.state.templates.TemplateResponse("eval.html", {
        "request": request,
        "score_cards": score_cards,
        "total_count": total_count,
        "overall_avg": overall_avg,
        "type_count": len(score_groups),
        "active_page": "eval",
        "api_error": api_error,
    })


# ---------------------------------------------------------------------------
# Review Inbox
# ---------------------------------------------------------------------------


@router.get("/reviews", response_class=HTMLResponse)
async def page_reviews(request: Request, threshold: float = Query(0.5, ge=0.0, le=1.0)):
    """Review Inbox — 낮은 점수 스코어 검토 큐."""
    from sentinel.config import lf_client

    scores = []
    api_error = ""
    try:
        res = lf_client.api.score_v_2.get(limit=100)
        data = res.data if hasattr(res, "data") else res
        for s in data:
            value = getattr(s, "value", None)
            if value is not None and value <= threshold:
                scores.append({
                    "score_id": getattr(s, "id", None),
                    "trace_id": getattr(s, "trace_id", None),
                    "name": getattr(s, "name", None) or "unknown",
                    "value": value,
                    "comment": getattr(s, "comment", None),
                    "timestamp": str(getattr(s, "timestamp", ""))[:19],
                })
        # 낮은 점수 순 정렬 (검토 필요한 것 먼저)
        scores.sort(key=lambda x: x["value"])
    except Exception as e:
        logger.exception("Langfuse score API 호출 실패 (Review Inbox)")
        api_error = f"Langfuse API 오류: {e}"

    # KPI 계산
    review_count = len(scores)
    values = [s["value"] for s in scores]
    avg_score = round(sum(values) / len(values), 3) if values else 0

    return request.app.state.templates.TemplateResponse("reviews.html", {
        "request": request,
        "scores": scores,
        "review_count": review_count,
        "avg_score": avg_score,
        "threshold": threshold,
        "active_page": "reviews",
        "api_error": api_error,
    })


@router.post("/reviews/{trace_id}/acknowledge")
async def action_acknowledge_review(request: Request, trace_id: str):
    """검토 완료 처리 — 해당 trace에 'reviewed' 스코어 추가."""
    from sentinel.config import lf_client

    try:
        lf_client.score(
            trace_id=trace_id,
            name="reviewed",
            value=1.0,
            comment="reviewed via inbox",
        )
    except Exception:
        logger.exception("Review acknowledge 실패: %s", trace_id)

    return RedirectResponse(url="/reviews", status_code=303)


# ---------------------------------------------------------------------------
# Alert Center
# ---------------------------------------------------------------------------


@router.get("/alerts", response_class=HTMLResponse)
async def page_alerts(request: Request):
    """Alert Center 메인 페이지."""
    from sentinel.alerts import alert_manager

    rules = alert_manager.list_rules()
    history = alert_manager.get_history(limit=50)
    return request.app.state.templates.TemplateResponse("alerts.html", {
        "request": request,
        "rules": rules,
        "history": history,
        "active_page": "alerts",
    })


@router.post("/alerts/rules")
async def create_alert_rule(
    request: Request,
    name: str = Form(...),
    metric: str = Form(...),
    operator: str = Form(...),
    threshold: float = Form(...),
    channel: str = Form("log"),
):
    """새 알림 규칙 생성."""
    from sentinel.alerts import alert_manager

    alert_manager.create_rule(
        name=name,
        metric=metric,
        operator=operator,
        threshold=threshold,
        channel=channel,
    )
    return RedirectResponse(url="/alerts", status_code=303)


@router.post("/alerts/rules/{rule_id}/toggle")
async def toggle_alert_rule(rule_id: int):
    """규칙 활성화/비활성화 토글."""
    from sentinel.alerts import alert_manager

    alert_manager.toggle_rule(rule_id)
    return RedirectResponse(url="/alerts", status_code=303)


@router.post("/alerts/rules/{rule_id}/delete")
async def delete_alert_rule(rule_id: int):
    """규칙 삭제."""
    from sentinel.alerts import alert_manager

    alert_manager.delete_rule(rule_id)
    return RedirectResponse(url="/alerts", status_code=303)


# ---------------------------------------------------------------------------
# Dataset Builder
# ---------------------------------------------------------------------------


@router.get("/datasets", response_class=HTMLResponse)
async def page_datasets(request: Request):
    """데이터셋 목록 페이지."""
    from sentinel.config import lf_client

    datasets = []
    api_error = ""
    try:
        res = lf_client.api.datasets.list()
        data = res.data if hasattr(res, "data") else res
        for ds in data:
            item_count = 0
            try:
                items_res = lf_client.api.dataset_items.list(dataset_name=ds.name)
                items_data = items_res.data if hasattr(items_res, "data") else items_res
                item_count = len(items_data)
            except Exception:
                pass
            datasets.append({
                "name": ds.name,
                "description": getattr(ds, "description", None),
                "item_count": item_count,
                "created_at": str(getattr(ds, "created_at", ""))[:19],
            })
    except Exception as e:
        logger.exception("Langfuse datasets list API 호출 실패")
        api_error = f"Langfuse API 오류: {e}"

    return request.app.state.templates.TemplateResponse("datasets.html", {
        "request": request,
        "datasets": datasets,
        "active_page": "datasets",
        "api_error": api_error,
    })


@router.post("/datasets")
async def create_dataset(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
):
    """새 데이터셋 생성."""
    from sentinel.config import lf_client

    try:
        lf_client.api.datasets.create(name=name, description=description)
    except Exception:
        logger.exception("데이터셋 생성 실패: %s", name)

    return RedirectResponse(url="/datasets", status_code=303)


@router.get("/datasets/{dataset_name}", response_class=HTMLResponse)
async def page_dataset_detail(request: Request, dataset_name: str):
    """데이터셋 상세 페이지."""
    from sentinel.config import lf_client

    dataset_name = unquote(dataset_name)

    items = []
    description = ""
    api_error = ""
    try:
        # 데이터셋 메타 정보 조회
        try:
            ds_res = lf_client.api.datasets.get(dataset_name=dataset_name)
            description = getattr(ds_res, "description", "") or ""
        except Exception:
            pass

        # 아이템 목록 조회
        res = lf_client.api.dataset_items.list(dataset_name=dataset_name)
        data = res.data if hasattr(res, "data") else res
        for item in data:
            input_str = str(getattr(item, "input", "") or "")
            output_str = str(getattr(item, "expected_output", "") or "")
            items.append({
                "id": item.id,
                "input_truncated": input_str[:100] + ("…" if len(input_str) > 100 else ""),
                "input_full": input_str,
                "output_truncated": output_str[:100] + ("…" if len(output_str) > 100 else ""),
                "output_full": output_str,
                "source_trace_id": getattr(item, "source_trace_id", None),
                "created_at": str(getattr(item, "created_at", ""))[:19],
            })
    except Exception as e:
        logger.exception("Langfuse dataset items API 호출 실패: %s", dataset_name)
        api_error = f"Langfuse API 오류: {e}"

    return request.app.state.templates.TemplateResponse("dataset_detail.html", {
        "request": request,
        "dataset_name": dataset_name,
        "description": description,
        "items": items,
        "active_page": "datasets",
        "api_error": api_error,
    })


@router.post("/datasets/{dataset_name}/items")
async def add_dataset_item(
    request: Request,
    dataset_name: str,
    trace_id: str = Form(...),
):
    """트레이스에서 데이터셋 아이템 추가."""
    from sentinel.config import lf_client

    dataset_name = unquote(dataset_name)

    try:
        # 트레이스 조회하여 input/output 가져오기
        t = lf_client.api.trace.get(trace_id)
        trace_input = getattr(t, "input", None)
        trace_output = getattr(t, "output", None)

        # 데이터셋 아이템 생성
        lf_client.api.dataset_items.create(
            dataset_name=dataset_name,
            input=trace_input,
            expected_output=trace_output,
            source_trace_id=trace_id,
        )
    except Exception:
        logger.exception("데이터셋 아이템 추가 실패: %s / trace %s", dataset_name, trace_id)

    return RedirectResponse(url=f"/datasets/{dataset_name}", status_code=303)


# ---------------------------------------------------------------------------
# Playbooks
# ---------------------------------------------------------------------------


@router.get("/playbooks", response_class=HTMLResponse)
async def page_playbooks(request: Request):
    """Playbook 목록 페이지."""
    from sentinel.playbook import playbook_manager

    playbooks = playbook_manager.list_all()
    return request.app.state.templates.TemplateResponse("playbooks.html", {
        "request": request,
        "playbooks": playbooks,
        "active_page": "playbooks",
    })


@router.get("/playbooks/{playbook_id}", response_class=HTMLResponse)
async def page_playbook_detail(request: Request, playbook_id: int):
    """Playbook 상세 페이지."""
    from sentinel.playbook import playbook_manager

    playbook = playbook_manager.get(playbook_id)
    if not playbook:
        return HTMLResponse("<h1>Playbook not found</h1>", status_code=404)

    runs = playbook_manager.get_runs(playbook_id, limit=20)
    return request.app.state.templates.TemplateResponse("playbook_detail.html", {
        "request": request,
        "playbook": playbook,
        "runs": runs,
        "active_page": "playbooks",
    })


@router.post("/playbooks")
async def create_playbook(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    steps_json: str = Form("[]"),
):
    """새 Playbook 생성."""
    import json
    from sentinel.playbook import playbook_manager

    try:
        steps = json.loads(steps_json)
    except (json.JSONDecodeError, TypeError):
        return HTMLResponse("Invalid JSON in steps", status_code=400)

    playbook_manager.create(name=name, description=description, steps=steps)
    return RedirectResponse(url="/playbooks", status_code=303)


@router.post("/playbooks/{playbook_id}/run")
async def run_playbook(request: Request, playbook_id: int):
    """Playbook 실행 (백그라운드 Job)."""
    from sentinel.playbook import playbook_manager

    job_id = playbook_manager.start_run(playbook_id)
    if not job_id:
        return HTMLResponse("<h1>Playbook not found</h1>", status_code=404)

    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@router.post("/playbooks/{playbook_id}/delete")
async def delete_playbook(playbook_id: int):
    """Playbook 삭제."""
    from sentinel.playbook import playbook_manager

    playbook_manager.delete(playbook_id)
    return RedirectResponse(url="/playbooks", status_code=303)


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
# Settings
# ---------------------------------------------------------------------------


def _mask_secret(value: str) -> str:
    """API 키 등 민감 정보를 마스킹합니다. 앞 4자만 표시."""
    if not value or len(value) <= 4:
        return "****"
    return value[:4] + "***"


@router.get("/settings", response_class=HTMLResponse)
async def page_settings(request: Request):
    """프로젝트 설정 페이지."""
    from sentinel.config import lf_client

    # --- 환경 변수 수집 ---
    _SECRET_KEYS = {"LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "SENTINEL_API_KEY"}
    env_vars = [
        ("SENTINEL_PROVIDER", os.environ.get("SENTINEL_PROVIDER", ""), "openai"),
        ("SENTINEL_MODEL", os.environ.get("SENTINEL_MODEL", ""), "gpt-5.4"),
        ("SENTINEL_FALLBACK_MODEL", os.environ.get("SENTINEL_FALLBACK_MODEL", ""), "gpt-4.1-mini"),
        ("LANGFUSE_HOST", os.environ.get("LANGFUSE_HOST", ""), "https://cloud.langfuse.com"),
        ("LANGFUSE_PUBLIC_KEY", os.environ.get("LANGFUSE_PUBLIC_KEY", ""), ""),
        ("SENTINEL_REPORTS_DIR", os.environ.get("SENTINEL_REPORTS_DIR", ""), "./reports"),
        ("SENTINEL_CHECKPOINT_DIR", os.environ.get("SENTINEL_CHECKPOINT_DIR", ""), "./checkpoints"),
        ("SENTINEL_ENABLE_SCHEDULER", os.environ.get("SENTINEL_ENABLE_SCHEDULER", ""), "false"),
        ("SENTINEL_AUTO_HTML", os.environ.get("SENTINEL_AUTO_HTML", ""), "false"),
        ("SENTINEL_TIMEZONE", os.environ.get("SENTINEL_TIMEZONE", ""), "UTC"),
    ]

    config_rows = []
    for key, raw_value, default_value in env_vars:
        if raw_value:
            display = _mask_secret(raw_value) if key in _SECRET_KEYS else raw_value
            source = "env"
        else:
            display = default_value if default_value else "(not set)"
            source = "default"
        config_rows.append({"key": key, "value": display, "source": source})

    # --- Langfuse 연결 상태 ---
    langfuse_status = "OK"
    langfuse_error = ""
    try:
        lf_client.api.trace.list(limit=1)
    except Exception as e:
        langfuse_status = "Error"
        langfuse_error = str(e)

    langfuse_host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

    # --- Storage 상태 ---
    reports_dir = Path(os.environ.get("SENTINEL_REPORTS_DIR", "./reports"))
    storage_ok = reports_dir.exists()
    report_file_count = 0
    if storage_ok:
        report_file_count = sum(
            1 for f in reports_dir.iterdir() if f.suffix in (".md", ".html")
        )

    # --- Scheduler 상태 ---
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        scheduler_status = "Disabled"
    elif scheduler.running:
        scheduler_status = "Running"
    else:
        scheduler_status = "Stopped"

    # --- 시스템 정보 ---
    python_version = sys.version.split()[0]
    pkg_versions = {}
    for pkg_name in ("sentinel", "langfuse", "langchain-core", "fastapi", "uvicorn"):
        try:
            from importlib.metadata import version as _pkg_version
            pkg_versions[pkg_name] = _pkg_version(pkg_name)
        except Exception:
            pkg_versions[pkg_name] = "—"

    return request.app.state.templates.TemplateResponse("settings.html", {
        "request": request,
        "active_page": "settings",
        "config_rows": config_rows,
        "langfuse_status": langfuse_status,
        "langfuse_error": langfuse_error,
        "langfuse_host": langfuse_host,
        "storage_ok": storage_ok,
        "report_file_count": report_file_count,
        "reports_dir": str(reports_dir),
        "scheduler_status": scheduler_status,
        "python_version": python_version,
        "pkg_versions": pkg_versions,
    })


# ---------------------------------------------------------------------------
# Health / Ready 엔드포인트
# ---------------------------------------------------------------------------

@router.get("/health")
async def health():
    """프로세스 헬스 체크."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


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
