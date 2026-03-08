"""Route 모듈 — 각 도메인별 라우터를 통합합니다."""

from fastapi import APIRouter

from sentinel.web.routes.auth import router as auth_router
from sentinel.web.routes.dashboard import router as dashboard_router
from sentinel.web.routes.reports import router as reports_router
from sentinel.web.routes.operations import router as operations_router
from sentinel.web.routes.admin import router as admin_router
from sentinel.web.routes.chat import router as chat_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(reports_router)
router.include_router(operations_router)
router.include_router(admin_router)
router.include_router(chat_router)
