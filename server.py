"""Sentinel 웹 서버 — FastAPI + 스케줄러.

사용법:
    # 개발
    python server.py

    # 프로덕션
    uvicorn server:app --host 0.0.0.0 --port 8000
"""

from sentinel.web.app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
