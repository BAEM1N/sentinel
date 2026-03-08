"""대시보드 라우트."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from sentinel.settings import list_reports

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def page_index(request: Request):
    """대시보드 페이지."""
    reports = list_reports()
    md_count = sum(1 for r in reports if r["type"] == "MD")
    html_count = sum(1 for r in reports if r["type"] == "HTML")
    return request.app.state.templates.TemplateResponse(request, "index.html", {
        "reports": reports[:10],
        "md_count": md_count,
        "html_count": html_count,
        "total": len(reports),
        "active_page": "dashboard",
    })
