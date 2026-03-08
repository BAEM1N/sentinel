"""라우트 통합 테스트 — 페이지 접근성 검증."""

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
