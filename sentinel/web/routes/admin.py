"""관리 라우트 — Settings, Scheduler, Audit, Jobs, Health."""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from sentinel.settings import REPORTS_DIR, CHECKPOINT_DIR, TIMEZONE

router = APIRouter()


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


@router.get("/jobs", response_class=HTMLResponse)
async def page_jobs(request: Request):
    from sentinel.services.job_manager import job_manager
    jobs = [j.to_dict() for j in job_manager.list_jobs(limit=50)]
    return request.app.state.templates.TemplateResponse(request, "jobs.html", {
        "jobs": jobs,
        "active_page": "jobs",
    })


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def page_job_detail(request: Request, job_id: str):
    from sentinel.services.job_manager import job_manager
    job = job_manager.get(job_id)
    if not job:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)
    return request.app.state.templates.TemplateResponse(request, "job_detail.html", {
        "job": job.to_dict(),
        "active_page": "jobs",
    })


@router.get("/api/jobs/{job_id}")
async def api_job_status(job_id: str):
    from sentinel.services.job_manager import job_manager
    job = job_manager.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return JSONResponse(job.to_dict())


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


@router.get("/audit", response_class=HTMLResponse)
async def page_audit(request: Request, limit: int = 50, run_id: str = ""):
    from sentinel.audit import audit_log
    logs = audit_log.query(limit=limit, run_id=run_id or None)
    return request.app.state.templates.TemplateResponse(request, "audit.html", {
        "logs": logs,
        "active_page": "audit",
    })


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


@router.get("/scheduler", response_class=HTMLResponse)
async def page_scheduler(request: Request):
    scheduler = getattr(request.app.state, "scheduler", None)
    tz_label = TIMEZONE
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
    return request.app.state.templates.TemplateResponse(request, "scheduler.html", {
        "running": running,
        "jobs": jobs,
        "active_page": "scheduler",
    })


@router.get("/api/scheduler/status")
async def scheduler_status(request: Request):
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
    if not value or len(value) <= 4:
        return "****"
    return value[:4] + "***"


@router.get("/settings", response_class=HTMLResponse)
async def page_settings(request: Request):
    import sentinel.config as config

    _SECRET_KEYS = {"LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "SENTINEL_API_KEY"}
    env_vars = [
        ("SENTINEL_PROVIDER", os.environ.get("SENTINEL_PROVIDER", ""), "openai"),
        ("SENTINEL_MODEL", os.environ.get("SENTINEL_MODEL", ""), "gpt-4.1"),
        ("SENTINEL_FALLBACK_MODEL", os.environ.get("SENTINEL_FALLBACK_MODEL", ""), "gpt-4.1-mini"),
        ("LANGFUSE_HOST", os.environ.get("LANGFUSE_HOST", ""), "https://cloud.langfuse.com"),
        ("LANGFUSE_PUBLIC_KEY", os.environ.get("LANGFUSE_PUBLIC_KEY", ""), ""),
        ("SENTINEL_REPORTS_DIR", os.environ.get("SENTINEL_REPORTS_DIR", ""), "./runtime/reports"),
        ("SENTINEL_CHECKPOINT_DIR", os.environ.get("SENTINEL_CHECKPOINT_DIR", ""), "./runtime/checkpoints"),
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

    langfuse_status = "OK"
    langfuse_error = ""
    try:
        config.get_lf_client().api.trace.list(limit=1)
    except Exception as e:
        langfuse_status = "Error"
        langfuse_error = str(e)

    langfuse_host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

    reports_dir = Path(REPORTS_DIR)
    storage_ok = reports_dir.exists()
    report_file_count = 0
    if storage_ok:
        report_file_count = sum(1 for f in reports_dir.iterdir() if f.suffix in (".md", ".html"))

    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        sched_status = "Disabled"
    elif scheduler.running:
        sched_status = "Running"
    else:
        sched_status = "Stopped"

    python_version = sys.version.split()[0]
    pkg_versions = {}
    for pkg_name in ("sentinel", "langfuse", "langchain-core", "fastapi", "uvicorn"):
        try:
            from importlib.metadata import version as _pkg_version
            pkg_versions[pkg_name] = _pkg_version(pkg_name)
        except Exception:
            pkg_versions[pkg_name] = "—"

    return request.app.state.templates.TemplateResponse(request, "settings.html", {
        "active_page": "settings",
        "config_rows": config_rows,
        "langfuse_status": langfuse_status,
        "langfuse_error": langfuse_error,
        "langfuse_host": langfuse_host,
        "storage_ok": storage_ok,
        "report_file_count": report_file_count,
        "reports_dir": str(reports_dir),
        "scheduler_status": sched_status,
        "python_version": python_version,
        "pkg_versions": pkg_versions,
    })


# ---------------------------------------------------------------------------
# Health / Ready
# ---------------------------------------------------------------------------


@router.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/ready")
async def readiness(request: Request):
    checks: dict[str, str] = {}

    try:
        import sentinel.config as config
        config.get_lf_client().api.trace.list(limit=1)
        checks["langfuse"] = "ok"
    except Exception as e:
        checks["langfuse"] = f"error: {e}"

    reports_path = Path(REPORTS_DIR)
    if reports_path.exists() and os.access(reports_path, os.W_OK):
        checks["storage"] = "ok"
    else:
        checks["storage"] = "error: reports dir not writable"

    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        checks["scheduler"] = "disabled"
    elif scheduler.running:
        checks["scheduler"] = "ok"
    else:
        checks["scheduler"] = "stopped"

    ready = all(v == "ok" for k, v in checks.items() if k != "scheduler")
    status_code = 200 if ready else 503
    return JSONResponse({"ready": ready, "checks": checks}, status_code=status_code)
