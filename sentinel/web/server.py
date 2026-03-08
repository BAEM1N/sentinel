"""Sentinel 웹 서버 — FastAPI + 스케줄러.

사용법:
    # 개발
    uv run python -m sentinel.web.server

    # 프로덕션
    uvicorn sentinel.web.server:app --host 0.0.0.0 --port 8000
"""

from sentinel.web.app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "sentinel.web.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes=["runtime/*", ".sentinel/*", "*.db", ".venv/*"],
    )
