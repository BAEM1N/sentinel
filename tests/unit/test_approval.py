"""승인 시스템 테스트."""

import json
import tempfile
import os

from sentinel.approval import ApprovalManager, ApprovalStatus


class TestApprovalManager:
    """ApprovalManager 기본 동작."""

    def setup_method(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.mgr = ApprovalManager(db_path=self._tmp.name)
        self.mgr._ensure_initialized()

    def teardown_method(self):
        os.unlink(self._tmp.name)

    def test_request_and_get(self):
        aid = self.mgr.request_approval(
            request_type="test_action",
            action_summary="Test summary",
            params={"key": "value"},
        )
        assert aid is not None
        item = self.mgr.get(aid)
        assert item is not None
        assert item["request_type"] == "test_action"
        assert item["status"] == ApprovalStatus.PENDING.value

    def test_approve(self):
        aid = self.mgr.request_approval("action", "summary")
        self.mgr.approve(aid, decided_by="admin", reason="ok")
        item = self.mgr.get(aid)
        assert item["status"] == ApprovalStatus.APPROVED.value

    def test_reject(self):
        aid = self.mgr.request_approval("action", "summary")
        self.mgr.reject(aid, decided_by="admin", reason="no")
        item = self.mgr.get(aid)
        assert item["status"] == ApprovalStatus.REJECTED.value

    def test_get_pending(self):
        self.mgr.request_approval("a", "s1")
        self.mgr.request_approval("b", "s2")
        aid3 = self.mgr.request_approval("c", "s3")
        self.mgr.approve(aid3, "admin")
        pending = self.mgr.get_pending()
        assert len(pending) == 2


class TestFindByTypeAndParam:
    """find_by_type_and_param param_key 버그 수정 검증."""

    def setup_method(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.mgr = ApprovalManager(db_path=self._tmp.name)
        self.mgr._ensure_initialized()

    def teardown_method(self):
        os.unlink(self._tmp.name)

    def test_finds_by_correct_param_key(self):
        """param_key가 실제로 사용되는지 확인."""
        self.mgr.request_approval(
            request_type="report_publish",
            action_summary="Publish report",
            params={"md_path": "/reports/daily.md", "html_path": "/reports/daily.html"},
        )
        # md_path 키로 검색
        result = self.mgr.find_by_type_and_param(
            request_type="report_publish",
            param_key="md_path",
            param_value="daily.md",
        )
        assert result is not None

        # html_path 키로 검색
        result2 = self.mgr.find_by_type_and_param(
            request_type="report_publish",
            param_key="html_path",
            param_value="daily.html",
        )
        assert result2 is not None

    def test_does_not_match_wrong_key(self):
        """다른 키의 값이 일치해도 지정한 param_key가 아니면 매치 안됨."""
        self.mgr.request_approval(
            request_type="report_publish",
            action_summary="Publish",
            params={"md_path": "/reports/test.md"},
        )
        # html_path 키로 검색 — md_path에만 값이 있으므로 None
        result = self.mgr.find_by_type_and_param(
            request_type="report_publish",
            param_key="html_path",
            param_value="test.md",
        )
        assert result is None

    def test_no_match_returns_none(self):
        result = self.mgr.find_by_type_and_param(
            request_type="nonexistent",
            param_key="key",
            param_value="value",
        )
        assert result is None
