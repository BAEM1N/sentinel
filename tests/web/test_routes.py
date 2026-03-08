"""라우트 통합 테스트 — 페이지 접근성 · CSRF · 렌더링 검증."""

import os
import json
import tempfile

import pytest
from fastapi.testclient import TestClient

from sentinel.web.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_client(client):
    """로그인된 클라이언트."""
    client.post("/login", data={"username": "admin", "password": "admin"})
    return client


def _get_csrf_token(auth_client) -> str:
    """세션에서 CSRF 토큰 추출."""
    from sentinel.auth import session_manager

    session_id = auth_client.cookies.get("sentinel_session")
    session = session_manager.get_session(session_id)
    return session["csrf_token"] if session else ""


class TestPublicRoutes:
    """인증 불필요 라우트."""

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_login_page(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_unauthenticated_redirect(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code in (302, 401)


class TestAuthenticatedRoutes:
    """인증 필요 라우트."""

    def test_dashboard(self, auth_client):
        resp = auth_client.get("/")
        assert resp.status_code == 200

    def test_chat(self, auth_client):
        resp = auth_client.get("/chat")
        assert resp.status_code == 200

    def test_reports(self, auth_client):
        resp = auth_client.get("/reports")
        assert resp.status_code == 200

    def test_alerts(self, auth_client):
        resp = auth_client.get("/alerts")
        assert resp.status_code == 200

    def test_approvals(self, auth_client):
        resp = auth_client.get("/approvals")
        assert resp.status_code == 200

    def test_playbooks(self, auth_client):
        resp = auth_client.get("/playbooks")
        assert resp.status_code == 200

    def test_settings(self, auth_client):
        resp = auth_client.get("/settings")
        assert resp.status_code == 200


class TestCSRF:
    """POST 요청 CSRF 검증."""

    def test_json_post_with_csrf_header_succeeds(self, auth_client):
        """X-CSRF-Token 헤더로 JSON POST 성공."""
        csrf = _get_csrf_token(auth_client)
        resp = auth_client.post(
            "/api/chat",
            headers={"Content-Type": "application/json", "X-CSRF-Token": csrf},
            content=json.dumps({"message": "hello", "thread_id": "test-1"}),
        )
        # chat은 SSE 스트림 반환 — 200이면 CSRF 통과
        assert resp.status_code == 200

    def test_json_post_without_csrf_rejected(self, auth_client):
        """CSRF 토큰 없는 JSON POST → 403."""
        resp = auth_client.post(
            "/api/chat",
            headers={"Content-Type": "application/json"},
            content=json.dumps({"message": "hello"}),
        )
        assert resp.status_code == 403

    def test_json_post_wrong_csrf_rejected(self, auth_client):
        """잘못된 CSRF 토큰 → 403."""
        resp = auth_client.post(
            "/api/chat",
            headers={
                "Content-Type": "application/json",
                "X-CSRF-Token": "wrong-token-value",
            },
            content=json.dumps({"message": "hello"}),
        )
        assert resp.status_code == 403


class TestReportsRendering:
    """Reports 페이지 HTML 렌더링 내용 검증."""

    def test_reports_page_contains_heading(self, auth_client):
        resp = auth_client.get("/reports")
        assert resp.status_code == 200
        assert "report" in resp.text.lower() or "보고서" in resp.text.lower()

    def test_reports_page_shows_files(self, auth_client, tmp_path):
        """runtime/reports에 파일이 있으면 목록에 표시."""
        # settings.REPORTS_DIR을 임시 디렉토리로 교체
        import sentinel.settings as settings

        orig = settings.REPORTS_DIR
        test_dir = tmp_path / "reports"
        test_dir.mkdir()
        (test_dir / "daily_2026-03-07.md").write_text("# Test Daily Report")
        settings.REPORTS_DIR = str(test_dir)
        try:
            resp = auth_client.get("/reports")
            assert resp.status_code == 200
            assert "daily_2026-03-07.md" in resp.text
        finally:
            settings.REPORTS_DIR = orig


class TestRemovedRoutes:
    """제거된 Langfuse 열화복제 라우트 — 404 확인."""

    def test_traces_removed(self, auth_client):
        assert auth_client.get("/traces").status_code == 404

    def test_prompts_removed(self, auth_client):
        assert auth_client.get("/prompts").status_code == 404

    def test_eval_removed(self, auth_client):
        assert auth_client.get("/eval").status_code == 404

    def test_datasets_removed(self, auth_client):
        assert auth_client.get("/datasets").status_code == 404
