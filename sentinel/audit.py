"""감사 로그 — 에이전트 액션 기록."""
import json
import logging
import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger("sentinel.audit")


class AuditLog:
    """SQLite 기반 감사 로그."""

    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.join(
            os.environ.get("SENTINEL_CHECKPOINT_DIR", ".sentinel/checkpoints"),
            "audit.db",
        )
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    run_id TEXT,
                    thread_id TEXT,
                    action TEXT NOT NULL,
                    tool_name TEXT,
                    input_summary TEXT,
                    output_summary TEXT,
                    is_mutation BOOLEAN DEFAULT FALSE,
                    before_state TEXT,
                    after_state TEXT,
                    status TEXT DEFAULT 'success',
                    error TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_run_id ON audit_log(run_id)
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

    def log(
        self,
        action,
        tool_name=None,
        input_summary=None,
        output_summary=None,
        is_mutation=False,
        before_state=None,
        after_state=None,
        run_id=None,
        thread_id=None,
        status="success",
        error=None,
        metadata=None,
    ):
        """감사 로그 기록."""
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO audit_log
                   (timestamp, run_id, thread_id, action, tool_name, input_summary,
                    output_summary, is_mutation, before_state, after_state, status, error, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.utcnow().isoformat() + "Z",
                    run_id,
                    thread_id,
                    action,
                    tool_name,
                    str(input_summary)[:500] if input_summary else None,
                    str(output_summary)[:500] if output_summary else None,
                    is_mutation,
                    json.dumps(before_state) if before_state else None,
                    json.dumps(after_state) if after_state else None,
                    status,
                    str(error)[:500] if error else None,
                    json.dumps(metadata) if metadata else None,
                ),
            )

    def query(
        self,
        limit=50,
        run_id=None,
        action=None,
        tool_name=None,
        mutations_only=False,
        from_ts=None,
        to_ts=None,
    ):
        """감사 로그 조회."""
        sql = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        if run_id:
            sql += " AND run_id = ?"
            params.append(run_id)
        if action:
            sql += " AND action = ?"
            params.append(action)
        if tool_name:
            sql += " AND tool_name = ?"
            params.append(tool_name)
        if mutations_only:
            sql += " AND is_mutation = 1"
        if from_ts:
            sql += " AND timestamp >= ?"
            params.append(from_ts)
        if to_ts:
            sql += " AND timestamp <= ?"
            params.append(to_ts)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def get_run_summary(self, run_id):
        """특정 run의 요약 정보."""
        with self._conn() as conn:
            row = conn.execute(
                """SELECT
                     COUNT(*) as total_actions,
                     SUM(CASE WHEN is_mutation THEN 1 ELSE 0 END) as mutations,
                     MIN(timestamp) as started_at,
                     MAX(timestamp) as ended_at,
                     SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors
                   FROM audit_log WHERE run_id = ?""",
                (run_id,),
            ).fetchone()
            return dict(row) if row else None


# 모듈 레벨 싱글턴
audit_log = AuditLog()
