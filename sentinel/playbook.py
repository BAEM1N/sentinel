"""Playbook — 사전 정의 워크플로 자동화."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

logger = logging.getLogger("sentinel.playbook")


VALID_STEP_TYPES = {"report", "batch_eval", "alert_check"}


class PlaybookManager:
    """SQLite 기반 Playbook 관리자."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.path.join(
            os.environ.get("SENTINEL_CHECKPOINT_DIR", ".sentinel/checkpoints"),
            "playbooks.db",
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
                CREATE TABLE IF NOT EXISTS playbooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    steps_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_run_at TEXT,
                    run_count INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playbook_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playbook_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'running',
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    results_json TEXT,
                    error TEXT,
                    FOREIGN KEY (playbook_id) REFERENCES playbooks(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_playbook_runs_playbook
                ON playbook_runs(playbook_id)
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

    def create(self, name: str, description: str, steps: list[dict]) -> dict:
        """Playbook 생성."""
        for i, step in enumerate(steps):
            st = step.get("type", "")
            if st not in VALID_STEP_TYPES:
                raise ValueError(
                    f"Step {i + 1}: 잘못된 type '{st}' (허용: {VALID_STEP_TYPES})"
                )
        self._ensure_initialized()
        now = datetime.now(timezone.utc).isoformat()
        steps_json = json.dumps(steps, ensure_ascii=False)
        with self._conn() as conn:
            cursor = conn.execute(
                """INSERT INTO playbooks (name, description, steps_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (name, description, steps_json, now, now),
            )
            playbook_id = cursor.lastrowid
        return {
            "id": playbook_id,
            "name": name,
            "description": description,
            "steps": steps,
            "created_at": now,
            "updated_at": now,
            "last_run_at": None,
            "run_count": 0,
        }

    def list_all(self) -> list[dict]:
        """전체 Playbook 목록."""
        self._ensure_initialized()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM playbooks ORDER BY id DESC"
            ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["steps"] = json.loads(d.pop("steps_json"))
                results.append(d)
            return results

    def get(self, playbook_id: int) -> dict | None:
        """단일 Playbook 조회 (steps 포함)."""
        self._ensure_initialized()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM playbooks WHERE id = ?", (playbook_id,)
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["steps"] = json.loads(d.pop("steps_json"))
            return d

    def delete(self, playbook_id: int) -> bool:
        """Playbook 삭제."""
        self._ensure_initialized()
        with self._conn() as conn:
            conn.execute("DELETE FROM playbook_runs WHERE playbook_id = ?", (playbook_id,))
            conn.execute("DELETE FROM playbooks WHERE id = ?", (playbook_id,))
        return True

    def start_run(self, playbook_id: int) -> str | None:
        """Playbook을 백그라운드 Job으로 실행하고 job_id를 반환합니다."""
        self._ensure_initialized()
        playbook = self.get(playbook_id)
        if not playbook:
            return None

        now = datetime.now(timezone.utc).isoformat()
        # run 레코드 생성
        with self._conn() as conn:
            cursor = conn.execute(
                """INSERT INTO playbook_runs (playbook_id, status, started_at)
                   VALUES (?, 'running', ?)""",
                (playbook_id, now),
            )
            run_id = cursor.lastrowid

        # Job Manager로 백그라운드 실행
        from sentinel.services.job_manager import job_manager

        job = job_manager.submit(
            "playbook_run",
            self._execute_steps,
            params={
                "playbook_id": playbook_id,
                "run_id": run_id,
                "steps": playbook["steps"],
            },
        )
        return job.id

    def get_runs(self, playbook_id: int, limit: int = 20) -> list[dict]:
        """실행 이력 조회."""
        self._ensure_initialized()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM playbook_runs WHERE playbook_id = ? ORDER BY id DESC LIMIT ?",
                (playbook_id, limit),
            ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                if d.get("results_json"):
                    d["results"] = json.loads(d.pop("results_json"))
                else:
                    d.pop("results_json", None)
                    d["results"] = None
                results.append(d)
            return results

    def _execute_steps(self, playbook_id: int, run_id: int, steps: list[dict]):
        """스텝을 순차 실행합니다."""
        results = []
        error_msg = None

        try:
            for i, step in enumerate(steps):
                step_type = step.get("type", "")
                params = step.get("params", {})
                logger.info(
                    "Playbook %s run %s — step %d: %s",
                    playbook_id, run_id, i + 1, step_type,
                )

                try:
                    result = self._run_step(step_type, params)
                    results.append({
                        "step": i + 1,
                        "type": step_type,
                        "status": "success",
                        "result": str(result)[:500],
                    })
                except Exception as e:
                    logger.exception(
                        "Playbook %s step %d (%s) 실패", playbook_id, i + 1, step_type
                    )
                    results.append({
                        "step": i + 1,
                        "type": step_type,
                        "status": "failed",
                        "error": str(e)[:500],
                    })
                    error_msg = f"Step {i + 1} ({step_type}) failed: {e}"
                    break

        except Exception as e:
            error_msg = f"Playbook execution error: {e}"
            logger.exception("Playbook %s run %s 실행 오류", playbook_id, run_id)

        # 결과 저장
        now = datetime.now(timezone.utc).isoformat()
        status = "failed" if error_msg else "completed"

        with self._conn() as conn:
            conn.execute(
                """UPDATE playbook_runs
                   SET status = ?, completed_at = ?, results_json = ?, error = ?
                   WHERE id = ?""",
                (status, now, json.dumps(results, ensure_ascii=False), error_msg, run_id),
            )
            conn.execute(
                """UPDATE playbooks
                   SET last_run_at = ?, run_count = run_count + 1, updated_at = ?
                   WHERE id = ?""",
                (now, now, playbook_id),
            )

        return {"status": status, "results": results, "error": error_msg}

    def _run_step(self, step_type: str, params: dict):
        """개별 스텝 타입별 실행."""
        if step_type == "report":
            from sentinel.services.report_service import ReportService

            svc = ReportService()
            result = svc.generate(
                period=params.get("period", "daily"),
                output_html=params.get("output_html", False),
                notify=params.get("notify", False),
            )
            return f"Report generated: {result.md_path}"

        if step_type == "batch_eval":
            from sentinel.tools.evaluation import batch_evaluate

            result = batch_evaluate.invoke({
                "sample_size": params.get("sample_size", 10),
                "criteria": params.get("criteria", "정확성,완전성"),
            })
            return result

        if step_type == "alert_check":
            from sentinel.alerts import alert_manager

            # 기본 메트릭 수집: Langfuse에서 최근 트레이스 통계 추출
            metrics_data: dict[str, float] = {}
            try:
                from sentinel.config import lf_client

                res = lf_client.api.trace.list(limit=50)
                data = res.data if hasattr(res, "data") else res
                if data:
                    latencies = [
                        getattr(t, "latency", None) for t in data
                        if getattr(t, "latency", None) is not None
                    ]
                    costs = [
                        getattr(t, "total_cost", None) for t in data
                        if getattr(t, "total_cost", None) is not None
                    ]
                    if latencies:
                        metrics_data["latency"] = sum(latencies) / len(latencies)
                    if costs:
                        metrics_data["cost"] = sum(costs) / len(costs)
            except Exception:
                logger.warning("Alert check: 메트릭 수집 실패, 빈 데이터로 진행")

            triggered = alert_manager.check_alerts(metrics_data)
            return f"Alert check done: {len(triggered)} triggered"

        msg = f"Unknown step type: {step_type}"
        raise ValueError(msg)


# 모듈 레벨 싱글턴
playbook_manager = PlaybookManager()
