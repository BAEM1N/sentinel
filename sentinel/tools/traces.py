"""트레이스 · 세션 조회 도구 (다중 필터 지원)."""

import json
import logging

from langchain.tools import tool

from sentinel.config import lf_client

logger = logging.getLogger("sentinel.tools.traces")


@tool
def list_traces(
    name: str = "",
    user_id: str = "",
    session_id: str = "",
    from_ts: str = "",
    to_ts: str = "",
    tags: str = "",
    environment: str = "",
    release: str = "",
    version: str = "",
    order_by: str = "",
    page: int = 1,
    limit: int = 20,
) -> str:
    """Langfuse에서 트레이스 목록을 다양한 필터로 조회합니다.

    Args:
        name: 트레이스 이름 필터
        user_id: 사용자 ID 필터
        session_id: 세션 ID 필터
        from_ts: 시작 날짜 (ISO8601, e.g. 2025-03-01)
        to_ts: 종료 날짜 (ISO8601, e.g. 2025-03-07)
        tags: 태그 필터 (쉼표 구분)
        environment: 환경 필터 (e.g. production, staging)
        release: 릴리스 필터
        version: 버전 필터
        order_by: 정렬 기준 (e.g. timestamp)
        page: 페이지 번호 (기본 1)
        limit: 최대 조회 수 (기본 20)
    """
    kwargs: dict = {"limit": limit}
    if name:
        kwargs["name"] = name
    if user_id:
        kwargs["user_id"] = user_id
    if session_id:
        kwargs["session_id"] = session_id
    if from_ts:
        kwargs["from_timestamp"] = from_ts
    if to_ts:
        kwargs["to_timestamp"] = to_ts
    if tags:
        kwargs["tags"] = [t.strip() for t in tags.split(",")]
    if environment:
        kwargs["environment"] = environment
    if release:
        kwargs["release"] = release
    if version:
        kwargs["version"] = version
    if order_by:
        kwargs["order_by"] = order_by
    if page > 1:
        kwargs["page"] = page

    try:
        res = lf_client.api.trace.list(**kwargs)
    except Exception as e:
        logger.exception("Langfuse trace list API 호출 실패")
        return json.dumps({"error": f"Langfuse API 오류: {e}"}, ensure_ascii=False)
    data = res.data if hasattr(res, "data") else res

    rows = []
    for t in data:
        rows.append(
            {
                "id": t.id,
                "name": getattr(t, "name", None),
                "timestamp": str(getattr(t, "timestamp", ""))[:19],
                "user_id": getattr(t, "user_id", None),
                "session_id": getattr(t, "session_id", None),
                "latency": getattr(t, "latency", None),
                "total_cost": getattr(t, "total_cost", None),
                "input_tokens": getattr(t, "input_tokens", None),
                "output_tokens": getattr(t, "output_tokens", None),
                "tags": getattr(t, "tags", []),
                "level": getattr(t, "level", None),
                "environment": getattr(t, "environment", None),
                "release": getattr(t, "release", None),
                "version": getattr(t, "version", None),
            }
        )
    return json.dumps(rows, ensure_ascii=False, indent=2, default=str)


@tool
def get_trace_detail(trace_id: str) -> str:
    """특정 트레이스의 상세 정보를 조회합니다 (observation, 스코어, 입출력, 메타데이터).

    Args:
        trace_id: 조회할 트레이스 ID
    """
    try:
        t = lf_client.api.trace.get(trace_id)
    except Exception as e:
        logger.exception("trace detail API 호출 실패: %s", trace_id)
        return json.dumps({"error": f"Langfuse API 오류: {e}"}, ensure_ascii=False)
    detail = {
        "id": t.id,
        "name": getattr(t, "name", None),
        "user_id": getattr(t, "user_id", None),
        "session_id": getattr(t, "session_id", None),
        "input": str(getattr(t, "input", ""))[:1000],
        "output": str(getattr(t, "output", ""))[:1000],
        "timestamp": str(getattr(t, "timestamp", "")),
        "latency": getattr(t, "latency", None),
        "total_cost": getattr(t, "total_cost", None),
        "metadata": getattr(t, "metadata", {}),
        "tags": getattr(t, "tags", []),
        "level": getattr(t, "level", None),
        "version": getattr(t, "version", None),
        "scores": [
            {"name": s.name, "value": s.value, "comment": getattr(s, "comment", "")}
            for s in (getattr(t, "scores", []) or [])
        ],
        "observations": [
            {
                "id": o.id,
                "type": getattr(o, "type", None),
                "name": getattr(o, "name", None),
                "model": getattr(o, "model", None),
                "latency": getattr(o, "latency", None),
                "level": getattr(o, "level", None),
            }
            for o in (getattr(t, "observations", []) or [])
        ],
    }
    return json.dumps(detail, ensure_ascii=False, indent=2, default=str)


@tool
def list_sessions(limit: int = 20) -> str:
    """Langfuse 세션 목록을 조회합니다.

    Args:
        limit: 최대 조회 수
    """
    try:
        res = lf_client.api.sessions.list(limit=limit)
    except Exception as e:
        logger.exception("sessions list API 호출 실패")
        return json.dumps({"error": f"Langfuse API 오류: {e}"}, ensure_ascii=False)
    data = res.data if hasattr(res, "data") else res
    rows = []
    for s in data:
        rows.append(
            {
                "id": s.id,
                "created_at": str(getattr(s, "created_at", ""))[:19],
                "trace_count": getattr(s, "count_traces", None),
            }
        )
    return json.dumps(rows, ensure_ascii=False, indent=2, default=str)
