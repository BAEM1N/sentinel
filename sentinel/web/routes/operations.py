"""운영 라우트 — Reviews, Alerts, Playbooks, Approvals."""

import json
import logging
from html import escape as html_escape

from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

router = APIRouter()
logger = logging.getLogger("sentinel.web")


# ---------------------------------------------------------------------------
# Reviews
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
        scores.sort(key=lambda x: x["value"])
    except Exception as e:
        logger.exception("Langfuse score API 호출 실패 (Review Inbox)")
        api_error = f"Langfuse API 오류: {e}"

    review_count = len(scores)
    values = [s["value"] for s in scores]
    avg_score = round(sum(values) / len(values), 3) if values else 0

    return request.app.state.templates.TemplateResponse(request, "reviews.html", {
        "scores": scores,
        "review_count": review_count,
        "avg_score": avg_score,
        "threshold": threshold,
        "active_page": "reviews",
        "api_error": api_error,
        "data_note": "최근 100건 스코어 기준",
    })


@router.post("/reviews/{trace_id}/acknowledge")
async def action_acknowledge_review(request: Request, trace_id: str):
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
# Alerts
# ---------------------------------------------------------------------------


@router.get("/alerts", response_class=HTMLResponse)
async def page_alerts(request: Request):
    from sentinel.alerts import alert_manager

    rules = alert_manager.list_rules()
    history = alert_manager.get_history(limit=50)
    return request.app.state.templates.TemplateResponse(request, "alerts.html", {
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
    from sentinel.alerts import alert_manager

    try:
        alert_manager.create_rule(
            name=name, metric=metric, operator=operator,
            threshold=threshold, channel=channel,
        )
    except ValueError as e:
        return HTMLResponse(f"<h1>입력 오류: {html_escape(str(e))}</h1>", status_code=400)
    return RedirectResponse(url="/alerts", status_code=303)


@router.post("/alerts/rules/{rule_id}/toggle")
async def toggle_alert_rule(rule_id: int):
    from sentinel.alerts import alert_manager
    alert_manager.toggle_rule(rule_id)
    return RedirectResponse(url="/alerts", status_code=303)


@router.post("/alerts/rules/{rule_id}/delete")
async def delete_alert_rule(rule_id: int):
    from sentinel.alerts import alert_manager
    alert_manager.delete_rule(rule_id)
    return RedirectResponse(url="/alerts", status_code=303)


# ---------------------------------------------------------------------------
# Approvals (HITL)
# ---------------------------------------------------------------------------


@router.get("/approvals", response_class=HTMLResponse)
async def page_approvals(request: Request):
    from sentinel.approval import approval_manager, ApprovalStatus

    pending = approval_manager.get_pending()
    all_items = approval_manager.list_all(limit=200)
    approved_count = sum(1 for a in all_items if a["status"] == ApprovalStatus.APPROVED.value)
    rejected_count = sum(1 for a in all_items if a["status"] == ApprovalStatus.REJECTED.value)
    history = [a for a in all_items if a["status"] != ApprovalStatus.PENDING.value]

    return request.app.state.templates.TemplateResponse(request, "approvals.html", {
        "pending": pending,
        "history": history,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "active_page": "approvals",
    })


@router.post("/approvals/{approval_id}/approve")
async def action_approve(request: Request, approval_id: str, reason: str = Form("")):
    from sentinel.approval import approval_manager
    decided_by = getattr(request.state, "user", None) or "unknown"
    approval_manager.approve(approval_id, decided_by=decided_by, reason=reason)
    return RedirectResponse(url="/approvals", status_code=303)


@router.post("/approvals/{approval_id}/reject")
async def action_reject(request: Request, approval_id: str, reason: str = Form("")):
    from sentinel.approval import approval_manager
    decided_by = getattr(request.state, "user", None) or "unknown"
    approval_manager.reject(approval_id, decided_by=decided_by, reason=reason)
    return RedirectResponse(url="/approvals", status_code=303)


@router.get("/api/approvals/pending")
async def api_approvals_pending():
    from sentinel.approval import approval_manager
    pending = approval_manager.get_pending()
    return JSONResponse({"pending": pending, "count": len(pending)})


# ---------------------------------------------------------------------------
# Playbooks
# ---------------------------------------------------------------------------


@router.get("/playbooks", response_class=HTMLResponse)
async def page_playbooks(request: Request):
    from sentinel.playbook import playbook_manager
    playbooks = playbook_manager.list_all()
    return request.app.state.templates.TemplateResponse(request, "playbooks.html", {
        "playbooks": playbooks,
        "active_page": "playbooks",
    })


@router.get("/playbooks/{playbook_id}", response_class=HTMLResponse)
async def page_playbook_detail(request: Request, playbook_id: int):
    from sentinel.playbook import playbook_manager
    playbook = playbook_manager.get(playbook_id)
    if not playbook:
        return HTMLResponse("<h1>Playbook not found</h1>", status_code=404)
    runs = playbook_manager.get_runs(playbook_id, limit=20)
    return request.app.state.templates.TemplateResponse(request, "playbook_detail.html", {
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
    from sentinel.playbook import playbook_manager

    try:
        steps = json.loads(steps_json)
    except (json.JSONDecodeError, TypeError):
        return HTMLResponse("Invalid JSON in steps", status_code=400)

    try:
        playbook_manager.create(name=name, description=description, steps=steps)
    except ValueError as e:
        return HTMLResponse(f"<h1>입력 오류: {html_escape(str(e))}</h1>", status_code=400)
    return RedirectResponse(url="/playbooks", status_code=303)


@router.post("/playbooks/{playbook_id}/run")
async def run_playbook(request: Request, playbook_id: int):
    from sentinel.playbook import playbook_manager
    job_id = playbook_manager.start_run(playbook_id)
    if not job_id:
        return HTMLResponse("<h1>Playbook not found</h1>", status_code=404)
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@router.post("/playbooks/{playbook_id}/delete")
async def delete_playbook(playbook_id: int):
    from sentinel.playbook import playbook_manager
    playbook_manager.delete(playbook_id)
    return RedirectResponse(url="/playbooks", status_code=303)
