"""인증 · 세션 관리 — Session Cookie + API Key 하이브리드."""

from __future__ import annotations

import logging
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import parse_qs

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, RedirectResponse

logger = logging.getLogger("sentinel.auth")

# 세션 유효 기간 (시간)
SESSION_TTL_HOURS = 24

# 인증 제외 경로
PUBLIC_PATHS = {"/login", "/health", "/ready"}


class SessionManager:
    """SQLite 기반 세션 관리자."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(
            os.environ.get("SENTINEL_CHECKPOINT_DIR", ".sentinel/checkpoints"),
            "sessions.db",
        )
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return
        dir_name = os.path.dirname(self.db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        self._init_db()
        self._initialized = True

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    csrf_token TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def create_session(self, username: str) -> dict:
        """새 세션 생성. session_id, csrf_token, username 반환."""
        self._ensure_initialized()
        # 확률적 만료 세션 정리 (약 10% 확률)
        if secrets.randbelow(10) == 0:
            cleaned = self.cleanup_expired()
            if cleaned:
                logger.info("만료 세션 %d건 정리됨", cleaned)
        session_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=SESSION_TTL_HOURS)

        with self._conn() as conn:
            conn.execute(
                """INSERT INTO sessions (session_id, username, csrf_token, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, username, csrf_token, now.isoformat(), expires_at.isoformat()),
            )
        return {
            "session_id": session_id,
            "csrf_token": csrf_token,
            "username": username,
        }

    def get_session(self, session_id: str) -> dict | None:
        """세션 조회. 만료된 세션은 삭제 후 None 반환."""
        self._ensure_initialized()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if not row:
                return None
            # 만료 체크
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                return None
            return dict(row)

    def delete_session(self, session_id: str):
        """세션 삭제 (로그아웃)."""
        self._ensure_initialized()
        with self._conn() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    def cleanup_expired(self) -> int:
        """만료 세션 일괄 삭제."""
        self._ensure_initialized()
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
            return cur.rowcount


def verify_credentials(username: str, password: str) -> bool:
    """환경변수의 admin 계정과 비교.

    기본 admin/admin 계정은 개발 모드에서만 허용됩니다.
    프로덕션에서는 SENTINEL_ADMIN_USER/SENTINEL_ADMIN_PASS를 반드시 설정하세요.
    """
    admin_user = os.environ.get("SENTINEL_ADMIN_USER", "")
    admin_pass = os.environ.get("SENTINEL_ADMIN_PASS", "")

    # 환경변수 미설정 시 개발용 기본 계정 (DEV 모드에서만)
    if not admin_user or not admin_pass:
        dev_mode = os.environ.get("SENTINEL_ENV", "development").lower() != "production"
        if dev_mode:
            admin_user = admin_user or "admin"
            admin_pass = admin_pass or "admin"
            logger.warning(
                "기본 관리자 계정(admin/admin) 사용 중 — "
                "SENTINEL_ADMIN_USER/SENTINEL_ADMIN_PASS 환경변수를 설정하세요."
            )
        else:
            logger.error("프로덕션 환경에서 관리자 계정이 설정되지 않았습니다.")
            return False

    return secrets.compare_digest(username, admin_user) and secrets.compare_digest(
        password, admin_pass
    )


# 모듈 레벨 싱글턴
session_manager = SessionManager()


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class AuthMiddleware(BaseHTTPMiddleware):
    """세션 쿠키 또는 X-API-Key 헤더 기반 인증 미들웨어."""

    async def dispatch(self, request, call_next):
        path = request.url.path

        # 정적/공개 경로 제외
        if path in PUBLIC_PATHS:
            request.state.user = None
            request.state.csrf_token = ""
            return await call_next(request)

        # 1) X-API-Key 헤더 (에이전트/API 접근)
        api_key = request.headers.get("x-api-key")
        if api_key:
            expected = os.environ.get("SENTINEL_WEB_API_KEY", "")
            if not expected or not secrets.compare_digest(api_key, expected):
                return JSONResponse({"error": "Invalid API key"}, status_code=401)
            request.state.user = "api-agent"
            request.state.csrf_token = ""
            return await call_next(request)

        # 2) 세션 쿠키 (브라우저 접근)
        session_id = request.cookies.get("sentinel_session")
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                request.state.user = session["username"]
                request.state.csrf_token = session["csrf_token"]

                # POST 요청 CSRF 검증
                if request.method == "POST":
                    body = await request.body()
                    form_data = parse_qs(body.decode("utf-8", errors="replace"))
                    form_csrf = form_data.get("_csrf_token", [""])[0]
                    if not secrets.compare_digest(form_csrf, session["csrf_token"]):
                        return JSONResponse(
                            {"error": "CSRF token mismatch"}, status_code=403
                        )

                return await call_next(request)

        # 3) 인증 실패
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(url="/login", status_code=302)
        return JSONResponse({"error": "Authentication required"}, status_code=401)
