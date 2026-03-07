"""플랫폼 관리 도구 — 데이터셋, 주석, think_tool."""

import json

from langchain.tools import tool

from sentinel.config import lf_client


@tool
def manage_datasets(
    action: str = "list",
    dataset_name: str = "",
    item_input: str = "",
    item_expected: str = "",
    source_trace_id: str = "",
    description: str = "",
) -> str:
    """데이터셋을 관리합니다 (list/create/add_item/list_items).

    Args:
        action: 작업 유형 (list, create, add_item, list_items)
        dataset_name: 데이터셋 이름 (create/add_item/list_items 시 필수)
        item_input: 아이템 입력 (add_item 시)
        item_expected: 기대 출력 (add_item 시)
        source_trace_id: 출처 트레이스 ID (add_item 시)
        description: 데이터셋 설명 (create 시)
    """
    if action == "list":
        res = lf_client.api.datasets.list(limit=50)
        data = res.data if hasattr(res, "data") else res
        return json.dumps(
            [
                {"name": d.name, "description": getattr(d, "description", "")}
                for d in data
            ],
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    elif action == "create":
        lf_client.api.datasets.create(name=dataset_name, description=description)
        return f"데이터셋 '{dataset_name}' 생성 완료"

    elif action == "add_item":
        kwargs: dict = {
            "dataset_name": dataset_name,
            "input": (
                json.loads(item_input)
                if item_input.startswith("{")
                else item_input
            ),
        }
        if item_expected:
            kwargs["expected_output"] = item_expected
        if source_trace_id:
            kwargs["source_trace_id"] = source_trace_id
        lf_client.api.dataset_items.create(**kwargs)
        return f"데이터셋 '{dataset_name}'에 아이템 추가 완료"

    elif action == "list_items":
        res = lf_client.api.dataset_items.list(
            dataset_name=dataset_name, limit=50
        )
        data = res.data if hasattr(res, "data") else res
        return json.dumps(
            [
                {"id": i.id, "input": str(getattr(i, "input", ""))[:200]}
                for i in data
            ],
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    return f"알 수 없는 action: {action}"


@tool
def manage_annotations(
    action: str = "list",
    object_type: str = "TRACE",
    object_id: str = "",
    content: str = "",
    author: str = "sentinel-agent",
) -> str:
    """트레이스/observation에 코멘트(주석)를 관리합니다.

    Args:
        action: 작업 (list, create)
        object_type: 대상 타입 (TRACE 또는 OBSERVATION)
        object_id: 대상 ID
        content: 코멘트 내용 (create 시)
        author: 작성자 ID
    """
    if action == "create":
        from langfuse.api.resources.comments.types import CreateCommentRequest

        lf_client.api.comments.create(
            request=CreateCommentRequest(
                object_type=object_type,
                object_id=object_id,
                content=content,
                author_user_id=author,
            )
        )
        return f"코멘트 작성 완료: {object_type} {object_id[:12]}..."

    res = lf_client.api.comments.get(
        object_type=object_type, object_id=object_id
    )
    data = res.data if hasattr(res, "data") else res
    return json.dumps(
        [
            {
                "id": c.id,
                "content": c.content,
                "author": getattr(c, "author_user_id", ""),
            }
            for c in data
        ],
        ensure_ascii=False,
        indent=2,
        default=str,
    )


@tool
def think_tool(thought: str) -> str:
    """전략적 반성 — 현재 상황을 분석하고 다음 행동을 계획합니다."""
    return f"Reflection recorded: {thought}"
