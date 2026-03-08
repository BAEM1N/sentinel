"""Sentinel 도구 모음 — 15개 커스텀 도구."""

from sentinel.tools.traces import get_trace_detail, list_sessions, list_traces
from sentinel.tools.prompt_mgmt import (
    get_langfuse_prompt,
    save_langfuse_prompt,
    suggest_prompt_improvement,
)
from sentinel.tools.evaluation import (
    batch_evaluate,
    create_score,
    evaluate_with_llm,
    list_scores,
)
from sentinel.tools.metrics import generate_report, query_metrics
from sentinel.tools.platform import manage_annotations, manage_datasets, query_audit_log, think_tool

all_tools = [
    # 트레이스/세션
    list_traces,
    get_trace_detail,
    list_sessions,
    # 프롬프트 관리
    get_langfuse_prompt,
    save_langfuse_prompt,
    suggest_prompt_improvement,
    # 평가/스코어
    list_scores,
    create_score,
    evaluate_with_llm,
    batch_evaluate,
    # Metrics/보고서
    query_metrics,
    generate_report,
    # 플랫폼 관리
    manage_datasets,
    manage_annotations,
    # 감사 로그
    query_audit_log,
    # 유틸리티
    think_tool,
]

# Audit log 싱글턴
from sentinel.audit import audit_log

__all__ = ["all_tools", "audit_log"] + [t.name for t in all_tools]
