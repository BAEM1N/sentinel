"""중앙 설정 — 경로·환경·기능 플래그를 한 곳에서 정의."""

import os
from datetime import datetime
from pathlib import Path


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# ---------------------------------------------------------------------------
# 환경
# ---------------------------------------------------------------------------

ENVIRONMENT = _env("SENTINEL_ENV", "development")
IS_PRODUCTION = ENVIRONMENT.lower() == "production"

# ---------------------------------------------------------------------------
# 디렉토리 경로 (단일 기본값)
# ---------------------------------------------------------------------------

REPORTS_DIR = _env("SENTINEL_REPORTS_DIR", "./runtime/reports")
CHECKPOINT_DIR = _env("SENTINEL_CHECKPOINT_DIR", "./runtime/checkpoints")
SKILLS_DIR = _env("SENTINEL_SKILLS_DIR", "./skills/")

# ---------------------------------------------------------------------------
# 에이전트
# ---------------------------------------------------------------------------

RUN_LIMIT = int(_env("SENTINEL_RUN_LIMIT", "30"))

# ---------------------------------------------------------------------------
# 스케줄러
# ---------------------------------------------------------------------------

SCHEDULER_ENABLED = _env("SENTINEL_ENABLE_SCHEDULER", "false").lower() == "true"
AUTO_HTML = _env("SENTINEL_AUTO_HTML", "false").lower() == "true"
TIMEZONE = _env("SENTINEL_TIMEZONE", "UTC")

# ---------------------------------------------------------------------------
# 유틸리티
# ---------------------------------------------------------------------------


def list_reports() -> list[dict]:
    """reports 디렉토리의 보고서 파일 목록을 수정시각 내림차순으로 반환합니다.

    반환 필드: name, type, period, size_kb, modified, filename
    """
    reports_path = Path(REPORTS_DIR)
    if not reports_path.exists():
        return []

    files = []
    for f in reports_path.iterdir():
        if f.suffix in (".md", ".html"):
            stat = f.stat()
            # 파일명에서 period 추론: daily_2026-03-08.md → daily
            stem = f.stem
            period = ""
            for p in ("daily", "weekly", "monthly"):
                if p in stem.lower():
                    period = p
                    break

            files.append({
                "name": f.name,
                "filename": f.name,
                "type": "HTML" if f.suffix == ".html" else "MD",
                "period": period,
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
    files.sort(key=lambda x: x["modified"], reverse=True)
    return files
