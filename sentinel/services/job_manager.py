"""백그라운드 Job 관리자 — in-process thread 기반."""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger("sentinel.services.jobs")


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class Job:
    id: str
    type: str
    status: JobStatus = JobStatus.QUEUED
    params: dict = field(default_factory=dict)
    result: Any = None
    error: str | None = None
    created_at: str = ""
    started_at: str | None = None
    completed_at: str | None = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status.value,
            "params": self.params,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class JobManager:
    """In-process job manager using threads."""

    def __init__(self, max_history: int = 100):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._max_history = max_history

    def submit(self, job_type: str, func, params: dict | None = None) -> Job:
        """새 Job을 제출하고 백그라운드에서 실행합니다."""
        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, type=job_type, params=params or {})

        with self._lock:
            self._jobs[job_id] = job
            self._trim_history()

        thread = threading.Thread(
            target=self._run_job,
            args=(job, func),
            daemon=True,
        )
        thread.start()
        return job

    def _run_job(self, job: Job, func):
        """Job 실행 wrapper."""
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow().isoformat() + "Z"

        try:
            result = func(**job.params)
            job.result = result
            job.status = JobStatus.SUCCEEDED
        except Exception as e:
            logger.exception("Job %s 실패", job.id)
            job.error = str(e)
            job.status = JobStatus.FAILED
        finally:
            job.completed_at = datetime.utcnow().isoformat() + "Z"

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 20, status: str = "") -> list[Job]:
        with self._lock:
            jobs = sorted(
                self._jobs.values(), key=lambda j: j.created_at, reverse=True
            )
        if status:
            jobs = [j for j in jobs if j.status.value == status]
        return jobs[:limit]

    def _trim_history(self):
        """오래된 완료 Job 정리."""
        if len(self._jobs) <= self._max_history:
            return
        completed = [
            (k, v)
            for k, v in self._jobs.items()
            if v.status in (JobStatus.SUCCEEDED, JobStatus.FAILED)
        ]
        completed.sort(key=lambda x: x[1].created_at)
        for k, _ in completed[: len(self._jobs) - self._max_history]:
            del self._jobs[k]


# 모듈 레벨 싱글턴
job_manager = JobManager()
