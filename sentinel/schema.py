"""도구 출력 표준 스키마."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ToolResult:
    """도구 출력 표준 envelope."""

    success: bool
    data: Any = None
    error: str | None = None
    summary: str = ""
    count: int | None = None
    total: int | None = None
    page: int | None = None
    has_more: bool = False

    def to_json(self) -> str:
        """JSON 문자열로 직렬화."""
        d = {k: v for k, v in asdict(self).items() if v is not None}
        return json.dumps(d, ensure_ascii=False, indent=2, default=str)

    @staticmethod
    def ok(
        data: Any,
        summary: str = "",
        count: int | None = None,
        total: int | None = None,
        page: int | None = None,
        has_more: bool = False,
    ) -> ToolResult:
        """성공 결과."""
        return ToolResult(
            success=True,
            data=data,
            summary=summary,
            count=count,
            total=total,
            page=page,
            has_more=has_more,
        )

    @staticmethod
    def fail(error: str, data: Any = None) -> ToolResult:
        """실패 결과."""
        return ToolResult(success=False, error=error, data=data)
