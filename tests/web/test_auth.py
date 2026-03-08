"""인증 시스템 테스트."""

import os
import pytest
from unittest.mock import patch

from sentinel.auth import verify_credentials, SessionManager


class TestVerifyCredentials:
    """verify_credentials 함수 테스트."""

    def test_default_dev_credentials(self):
        """개발 모드에서 기본 admin/admin 허용."""
        with patch.dict(os.environ, {"SENTINEL_ENV": "development"}, clear=False):
            os.environ.pop("SENTINEL_ADMIN_USER", None)
            os.environ.pop("SENTINEL_ADMIN_PASS", None)
            assert verify_credentials("admin", "admin") is True

    def test_wrong_credentials(self):
        """잘못된 인증 거부."""
        with patch.dict(os.environ, {
            "SENTINEL_ADMIN_USER": "myuser",
            "SENTINEL_ADMIN_PASS": "mypass",
        }):
            assert verify_credentials("wrong", "wrong") is False

    def test_custom_credentials(self):
        """커스텀 계정 인증 성공."""
        with patch.dict(os.environ, {
            "SENTINEL_ADMIN_USER": "myuser",
            "SENTINEL_ADMIN_PASS": "mypass",
        }):
            assert verify_credentials("myuser", "mypass") is True

    def test_production_blocks_default(self):
        """프로덕션 모드에서 미설정 시 인증 거부."""
        env = {"SENTINEL_ENV": "production"}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("SENTINEL_ADMIN_USER", None)
            os.environ.pop("SENTINEL_ADMIN_PASS", None)
            assert verify_credentials("admin", "admin") is False


class TestSessionManager:
    """SessionManager 테스트."""

    def setup_method(self, tmp_path=None):
        import tempfile
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.mgr = SessionManager(self._tmp.name)
        self.mgr._ensure_initialized()

    def teardown_method(self):
        import os
        os.unlink(self._tmp.name)

    def test_create_and_get_session(self):
        session = self.mgr.create_session("testuser")
        assert session["username"] == "testuser"
        assert "session_id" in session
        assert "csrf_token" in session

        retrieved = self.mgr.get_session(session["session_id"])
        assert retrieved is not None
        assert retrieved["username"] == "testuser"

    def test_delete_session(self):
        session = self.mgr.create_session("testuser")
        self.mgr.delete_session(session["session_id"])
        assert self.mgr.get_session(session["session_id"]) is None

    def test_invalid_session(self):
        assert self.mgr.get_session("nonexistent") is None
