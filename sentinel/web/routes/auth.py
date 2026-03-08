"""인증 라우트 — 로그인/로그아웃."""

import os

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

def _is_secure() -> bool:
    """HTTPS 환경 여부 판단. 프로덕션이면 secure=True."""
    return os.environ.get("SENTINEL_ENV", "development").lower() == "production"


@router.get("/login", response_class=HTMLResponse)
async def page_login(request: Request):
    return request.app.state.templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def action_login(request: Request, username: str = Form(...), password: str = Form(...)):
    from sentinel.auth import verify_credentials, session_manager

    if not verify_credentials(username, password):
        return request.app.state.templates.TemplateResponse(
            request, "login.html", {"error": "Invalid username or password."},
            status_code=401,
        )

    old_session_id = request.cookies.get("sentinel_session")
    if old_session_id:
        session_manager.delete_session(old_session_id)

    session = session_manager.create_session(username)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="sentinel_session",
        value=session["session_id"],
        httponly=True,
        samesite="lax",
        secure=_is_secure(),
        max_age=24 * 3600,
    )
    return response


@router.post("/logout")
async def action_logout(request: Request):
    from sentinel.auth import session_manager

    session_id = request.cookies.get("sentinel_session")
    if session_id:
        session_manager.delete_session(session_id)

    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("sentinel_session")
    return response
