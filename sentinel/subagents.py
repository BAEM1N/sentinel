"""서브에이전트 3개 정의 — trace-analyst, prompt-optimizer, quality-evaluator."""

from sentinel.tools.traces import get_trace_detail, list_sessions, list_traces
from sentinel.tools.prompt_mgmt import (
    get_langfuse_prompt,
    save_langfuse_prompt,
    suggest_prompt_improvement,
)
from sentinel.tools.evaluation import create_score, evaluate_with_llm, list_scores
from sentinel.tools.metrics import generate_report, query_metrics
from sentinel.tools.platform import think_tool

trace_analyst = {
    "name": "trace-analyst",
    "description": (
        "트레이스/세션 데이터를 심층 분석하여 "
        "성능 병목, 에러 패턴, 비용 이상을 발견합니다"
    ),
    "system_prompt": (
        "당신은 LLMOps 트레이스 분석 전문가입니다.\n"
        "트레이스/세션 데이터를 분석하여 성능 병목, 에러 패턴, 비용 이상을 발견하세요.\n"
        "필터를 적극 활용하세요: user_id, session_id, 날짜 범위, 태그\n"
        "query_metrics로 집계 데이터를 확인하고, 개별 트레이스로 드릴다운하세요.\n"
        "분석 전 think_tool로 전략을 수립하고, 수치는 표로 정리하세요.\n"
        "최종 결과에 '핵심 발견', '권장 조치'를 포함하세요."
    ),
    "tools": [list_traces, get_trace_detail, list_sessions, query_metrics, think_tool],
}

prompt_optimizer = {
    "name": "prompt-optimizer",
    "description": "프롬프트를 분석하고 트레이스 데이터 기반으로 개선안을 제안합니다",
    "system_prompt": (
        "당신은 프롬프트 엔지니어링 전문가입니다.\n"
        "1. get_langfuse_prompt로 현재 프롬프트 조회\n"
        "2. list_traces로 관련 트레이스 수집 (저품질 응답 중심)\n"
        "3. suggest_prompt_improvement로 개선안 생성\n"
        "4. before/after를 명확히 보여주고, staging 라벨로 저장\n"
        "A/B 비교 시 버전별 성능 지표를 표로 정리하세요."
    ),
    "tools": [
        get_langfuse_prompt,
        save_langfuse_prompt,
        suggest_prompt_improvement,
        list_traces,
        list_scores,
        think_tool,
    ],
}

quality_evaluator = {
    "name": "quality-evaluator",
    "description": "LLM-as-judge로 트레이스 품질을 자동 평가하고 보고서를 생성합니다",
    "system_prompt": (
        "당신은 LLM 품질 평가 전문가입니다.\n"
        "1. list_traces로 평가 대상 선정\n"
        "2. evaluate_with_llm으로 자동 평가 실행\n"
        "3. 평가 결과를 종합하여 품질 트렌드 분석\n"
        "4. generate_report로 보고서 생성\n"
        "평가 기준: 정확성, 완전성, 유용성, 안전성, 일관성"
    ),
    "tools": [
        evaluate_with_llm,
        list_scores,
        create_score,
        list_traces,
        get_trace_detail,
        generate_report,
        think_tool,
    ],
}

all_subagents = [trace_analyst, prompt_optimizer, quality_evaluator]
