"""Agent Chat 라우트 — SSE 기반 실시간 스트리밍 채팅."""

import json
import logging
import uuid

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse

router = APIRouter()
logger = logging.getLogger("sentinel.web")


@router.get("/chat", response_class=HTMLResponse)
async def page_chat(request: Request):
    """Agent Chat 페이지."""
    return request.app.state.templates.TemplateResponse(request, "chat.html", {
        "active_page": "chat",
    })


@router.post("/api/chat")
async def api_chat(request: Request):
    """Agent 질의 API — SSE 스트리밍 응답."""
    body = await request.json()
    message = body.get("message", "").strip()
    thread_id = body.get("thread_id") or str(uuid.uuid4())[:8]

    if not message:
        return {"error": "message is required"}

    async def event_stream():
        try:
            from sentinel.agent import create_sentinel_agent
            from sentinel.config import lf_config

            agent = create_sentinel_agent()
            config = {"configurable": {"thread_id": f"sentinel-{thread_id}"}, **lf_config}

            # 스트리밍 실행
            final_content = ""
            for event in agent.stream(
                {"messages": [{"role": "user", "content": message}]},
                config=config,
                stream_mode="messages",
            ):
                msg, metadata = event if isinstance(event, tuple) else (event, {})
                if hasattr(msg, "content") and msg.content:
                    final_content += msg.content
                    yield f"data: {json.dumps({'type': 'token', 'content': msg.content}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'thread_id': thread_id}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.exception("Agent chat 실행 실패")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
