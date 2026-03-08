"""엔트리포인트 래퍼 — sentinel.web.server로 위임."""
from sentinel.web.server import app  # noqa: F401

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "sentinel.web.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes=["runtime/*", ".sentinel/*", "*.db", ".venv/*"],
    )
