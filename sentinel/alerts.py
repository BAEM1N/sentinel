"""알림 규칙 — 조건 기반 트리거."""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("sentinel.alerts")


VALID_OPERATORS = {"gt", "lt", "eq"}
VALID_METRICS = {"latency", "cost", "error_rate", "score"}
VALID_CHANNELS = {"log", "telegram", "email", "slack"}


class AlertRule:
    """알림 규칙 데이터 클래스."""

    def __init__(
        self,
        id: int,
        name: str,
        metric: str,
        operator: str,
        threshold: float,
        channel: str,
        enabled: bool = True,
        created_at: str = "",
        last_triggered_at: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.metric = metric
        self.operator = operator
        self.threshold = threshold
        self.channel = channel
        self.enabled = enabled
        self.created_at = created_at
        self.last_triggered_at = last_triggered_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "metric": self.metric,
            "operator": self.operator,
            "threshold": self.threshold,
            "channel": self.channel,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "last_triggered_at": self.last_triggered_at,
        }

    def condition_label(self) -> str:
        """사람이 읽을 수 있는 조건 문자열."""
        op_map = {"gt": ">", "lt": "<", "eq": "="}
        return f"{op_map.get(self.operator, self.operator)} {self.threshold}"

    def evaluate(self, value: float) -> bool:
        """값이 조건을 만족하는지 평가."""
        if self.operator == "gt":
            return value > self.threshold
        if self.operator == "lt":
            return value < self.threshold
        if self.operator == "eq":
            return abs(value - self.threshold) < 1e-9
        return False


class AlertManager:
    """SQLite 기반 알림 규칙 관리자."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(
            os.environ.get("SENTINEL_CHECKPOINT_DIR", ".sentinel/checkpoints"),
            "alerts.db",
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
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    operator TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    channel TEXT NOT NULL DEFAULT 'log',
                    enabled BOOLEAN DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_triggered_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id INTEGER NOT NULL,
                    rule_name TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    operator TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'triggered',
                    triggered_at TEXT NOT NULL,
                    FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alert_history_triggered
                ON alert_history(triggered_at)
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

    def create_rule(
        self,
        name: str,
        metric: str,
        operator: str,
        threshold: float,
        channel: str = "log",
    ) -> AlertRule:
        """알림 규칙 생성."""
        if operator not in VALID_OPERATORS:
            raise ValueError(f"잘못된 operator: {operator} (허용: {VALID_OPERATORS})")
        if metric not in VALID_METRICS:
            raise ValueError(f"잘못된 metric: {metric} (허용: {VALID_METRICS})")
        if channel not in VALID_CHANNELS:
            raise ValueError(f"잘못된 channel: {channel} (허용: {VALID_CHANNELS})")
        self._ensure_initialized()
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cursor = conn.execute(
                """INSERT INTO alert_rules (name, metric, operator, threshold, channel, enabled, created_at)
                   VALUES (?, ?, ?, ?, ?, 1, ?)""",
                (name, metric, operator, threshold, channel, now),
            )
            rule_id = cursor.lastrowid
        return AlertRule(
            id=rule_id,
            name=name,
            metric=metric,
            operator=operator,
            threshold=threshold,
            channel=channel,
            enabled=True,
            created_at=now,
        )

    def list_rules(self) -> list[AlertRule]:
        """전체 규칙 목록."""
        self._ensure_initialized()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM alert_rules ORDER BY id DESC"
            ).fetchall()
            return [AlertRule(**dict(r)) for r in rows]

    def update_rule(self, rule_id: int, **kwargs) -> bool:
        """규칙 수정."""
        self._ensure_initialized()
        if not kwargs:
            return False
        allowed = {"name", "metric", "operator", "threshold", "channel", "enabled"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [rule_id]
        with self._conn() as conn:
            conn.execute(
                f"UPDATE alert_rules SET {set_clause} WHERE id = ?",  # noqa: S608
                values,
            )
        return True

    def delete_rule(self, rule_id: int) -> bool:
        """규칙 삭제."""
        self._ensure_initialized()
        with self._conn() as conn:
            conn.execute("DELETE FROM alert_rules WHERE id = ?", (rule_id,))
        return True

    def toggle_rule(self, rule_id: int) -> bool:
        """enabled 토글."""
        self._ensure_initialized()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT enabled FROM alert_rules WHERE id = ?", (rule_id,)
            ).fetchone()
            if not row:
                return False
            new_val = 0 if row["enabled"] else 1
            conn.execute(
                "UPDATE alert_rules SET enabled = ? WHERE id = ?", (new_val, rule_id)
            )
        return True

    def check_alerts(self, metrics_data: dict[str, float]) -> list[dict]:
        """조건 평가 후 트리거된 알림 반환.

        Args:
            metrics_data: {"latency": 1.5, "cost": 0.03, "error_rate": 0.1, "score": 0.8}

        Returns:
            트리거된 알림 정보 리스트
        """
        self._ensure_initialized()
        rules = self.list_rules()
        triggered = []
        now = datetime.now(timezone.utc).isoformat()

        for rule in rules:
            if not rule.enabled:
                continue
            value = metrics_data.get(rule.metric)
            if value is None:
                continue
            if rule.evaluate(value):
                triggered.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "metric": rule.metric,
                    "value": value,
                    "threshold": rule.threshold,
                    "operator": rule.operator,
                    "channel": rule.channel,
                })

        # 트리거된 알림 이력을 단일 커넥션으로 일괄 저장
        if triggered:
            with self._conn() as conn:
                for item in triggered:
                    conn.execute(
                        """INSERT INTO alert_history
                           (rule_id, rule_name, metric, value, threshold, operator, channel, status, triggered_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, 'triggered', ?)""",
                        (
                            item["rule_id"],
                            item["rule_name"],
                            item["metric"],
                            item["value"],
                            item["threshold"],
                            item["operator"],
                            item["channel"],
                            now,
                        ),
                    )
                    conn.execute(
                        "UPDATE alert_rules SET last_triggered_at = ? WHERE id = ?",
                        (now, item["rule_id"]),
                    )
                    logger.info(
                        "Alert triggered: %s — %s %s %s (actual: %s)",
                        item["rule_name"],
                        item["metric"],
                        item["operator"],
                        item["threshold"],
                        item["value"],
                    )

        return triggered

    def get_history(self, limit: int = 50) -> list[dict]:
        """알림 발생 이력."""
        self._ensure_initialized()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM alert_history ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]


# 모듈 레벨 싱글턴
alert_manager = AlertManager()
