"""대시보드 라우트."""

import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

REPORTS_DIR = os.environ.get("SENTINEL_REPORTS_DIR", "./runtime/reports")


def _list_reports() -> list[dict]:
    """reports 디렉토리의 보고서 파일 목록을 수정시각 내림차순으로 반환합니다."""
    reports_path = Path(REPORTS_DIR)
    if not reports_path.exists():
        return []

    files = []
    for f in reports_path.iterdir():
        if f.suffix in (".md", ".html"):
            stat = f.stat()
            files.append({
                "filename": f.name,
                "type": "HTML" if f.suffix == ".html" else "MD",
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })
    files.sort(key=lambda x: x["modified"], reverse=True)
    return files


@router.get("/", response_class=HTMLResponse)
async def page_index(request: Request):
    """대시보드 페이지."""
    reports = _list_reports()
    md_count = sum(1 for r in reports if r["type"] == "MD")
    html_count = sum(1 for r in reports if r["type"] == "HTML")
    return request.app.state.templates.TemplateResponse(request, "index.html", {
        "reports": reports[:10],
        "md_count": md_count,
        "html_count": html_count,
        "total": len(reports),
        "active_page": "dashboard",
    })
