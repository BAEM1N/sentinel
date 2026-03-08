"""HITL 승인 워크플로 — 에이전트 액션 승인/거절 관리."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger("sentinel.approval")


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalManager:
    """SQLite 기반 승인 요청 관리."""

    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.join(
            os.environ.get("SENTINEL_CHECKPOINT_DIR", ".sentinel/checkpoints"),
            "approvals.db",
        )
        self._initialized = False

    def _ensure_initialized(self):
        """DB 초기화를 첫 사용 시까지 지연합니다."""
        if self._initialized:
            return
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        self._initialized = True

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS approvals (
                    id TEXT PRIMARY KEY,
                    request_type TEXT NOT NULL,
                    action_summary TEXT NOT NULL,
                    params_json TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    requested_at TEXT NOT NULL,
                    decided_at TEXT,
                    decided_by TEXT,
                    reason TEXT,
                    expires_at TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_approvals_status
                ON approvals(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_approvals_requested_at
                ON approvals(requested_at)
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

    def request_approval(
        self,
        request_type: str,
        action_summary: str,
        params: dict | None = None,
        expires_in_hours: int = 24,
    ) -> str:
        """새 승인 요청을 생성합니다. approval_id를 반환합니다."""
        self._ensure_initialized()
        approval_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(hours=expires_in_hours)).isoformat()

        with self._conn() as conn:
            conn.execute(
                """INSERT INTO approvals
                   (id, request_type, action_summary, params_json, status, requested_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    approval_id,
                    request_type,
                    action_summary,
                    json.dumps(params) if params else None,
                    ApprovalStatus.PENDING.value,
                    now.isoformat(),
                    expires_at,
                ),
            )
        logger.info("승인 요청 생성: %s (%s)", approval_id, request_type)
        return approval_id

    def get_pending(self) -> list[dict]:
        """대기 중인 승인 요청 목록을 반환합니다."""
        self._ensure_initialized()
        self.expire_old()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM approvals WHERE status = ? ORDER BY requested_at DESC",
                (ApprovalStatus.PENDING.value,),
            ).fetchall()
            return [dict(row) for row in rows]

    def approve(self, approval_id: str, decided_by: str, reason: str = "") -> bool:
        """승인 처리합니다."""
        self._ensure_initialized()
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """UPDATE approvals
                   SET status = ?, decided_at = ?, decided_by = ?, reason = ?
                   WHERE id = ? AND status = ?""",
                (
                    ApprovalStatus.APPROVED.value,
                    now,
                    decided_by,
                    reason,
                    approval_id,
                    ApprovalStatus.PENDING.value,
                ),
            )
            if cur.rowcount == 0:
                logger.warning("승인 처리 실패 (이미 처리됨 또는 없음): %s", approval_id)
                return False
        logger.info("승인 완료: %s by %s", approval_id, decided_by)
        return True

    def reject(self, approval_id: str, decided_by: str, reason: str = "") -> bool:
        """거절 처리합니다."""
        self._ensure_initialized()
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """UPDATE approvals
                   SET status = ?, decided_at = ?, decided_by = ?, reason = ?
                   WHERE id = ? AND status = ?""",
                (
                    ApprovalStatus.REJECTED.value,
                    now,
                    decided_by,
                    reason,
                    approval_id,
                    ApprovalStatus.PENDING.value,
                ),
            )
            if cur.rowcount == 0:
                logger.warning("거절 처리 실패 (이미 처리됨 또는 없음): %s", approval_id)
                return False
        logger.info("거절 완료: %s by %s", approval_id, decided_by)
        return True

    def get(self, approval_id: str) -> dict | None:
        """단일 승인 요청을 조회합니다."""
        self._ensure_initialized()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM approvals WHERE id = ?",
                (approval_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_all(
        self,
        limit: int = 50,
        status_filter: str | None = None,
    ) -> list[dict]:
        """전체 승인 요청을 조회합니다."""
        self._ensure_initialized()
        sql = "SELECT * FROM approvals WHERE 1=1"
        params: list = []
        if status_filter:
            sql += " AND status = ?"
            params.append(status_filter)
        sql += " ORDER BY requested_at DESC LIMIT ?"
        params.append(limit)

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def find_by_type_and_param(
        self,
        request_type: str,
        param_key: str,
        param_value: str,
        status_filter: str | None = None,
    ) -> dict | None:
        """request_type과 params_json 내 특정 키-값으로 승인 요청을 검색합니다."""
        self._ensure_initialized()
        sql = "SELECT * FROM approvals WHERE request_type = ?"
        params: list = [request_type]
        if status_filter:
            sql += " AND status = ?"
            params.append(status_filter)
        sql += " ORDER BY requested_at DESC"

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            for row in rows:
                row_dict = dict(row)
                if row_dict.get("params_json"):
                    try:
                        p = json.loads(row_dict["params_json"])
                        stored = p.get(param_key, "")
                        if stored and os.path.basename(stored) == param_value:
                            return row_dict
                    except (json.JSONDecodeError, TypeError):
                        pass
        return None

    def expire_old(self) -> int:
        """만료된 대기 항목을 expired 상태로 변경합니다. 변경 건수를 반환합니다."""
        self._ensure_initialized()
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """UPDATE approvals
                   SET status = ?, decided_at = ?
                   WHERE status = ? AND expires_at < ?""",
                (
                    ApprovalStatus.EXPIRED.value,
                    now,
                    ApprovalStatus.PENDING.value,
                    now,
                ),
            )
            if cur.rowcount > 0:
                logger.info("만료 처리: %d건", cur.rowcount)
            return cur.rowcount


# 모듈 레벨 싱글턴
approval_manager = ApprovalManager()
