"""FastAPI 앱 팩토리."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

logger = logging.getLogger("sentinel.web")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 스케줄러 관리.

    SENTINEL_ENABLE_SCHEDULER=false 로 비활성화할 수 있습니다.
    멀티 인스턴스 배포 시 하나의 인스턴스에서만 활성화하세요.
    """
    enable = os.environ.get("SENTINEL_ENABLE_SCHEDULER", "true").lower()
    if enable in ("true", "1", "yes"):
        from sentinel.web.scheduler import create_scheduler

        scheduler = create_scheduler()
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("scheduler started: daily(00:00), weekly(Mon 00:00), monthly(1st 00:00)")
    else:
        logger.info("scheduler disabled (SENTINEL_ENABLE_SCHEDULER=%s)", enable)
    yield
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler is not None:
        scheduler.shutdown()
        logger.info("scheduler stopped")


def create_app() -> FastAPI:
    """FastAPI 앱을 생성합니다."""
    logging.basicConfig(
        level=logging.INFO,
        format="[sentinel] %(levelname)s %(name)s — %(message)s",
    )

    app = FastAPI(
        title="Sentinel",
        description="Langfuse LLMOps Agent",
        version="0.0.1",
        lifespan=lifespan,
    )

    # Jinja2 템플릿
    templates_dir = Path(__file__).parent.parent / "templates"
    app.state.templates = Jinja2Templates(directory=str(templates_dir))

    # runtime 디렉토리 초기화
    reports_dir = os.environ.get("SENTINEL_REPORTS_DIR", "./runtime/reports")
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(os.environ.get("SENTINEL_CHECKPOINT_DIR", "./runtime/checkpoints"), exist_ok=True)

    # 인증 미들웨어
    from sentinel.auth import AuthMiddleware
    app.add_middleware(AuthMiddleware)

    # 라우트 등록
    from sentinel.web.routes import router
    app.include_router(router)

    return app
