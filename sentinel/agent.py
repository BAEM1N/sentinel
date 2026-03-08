"""Sentinel 에이전트 생성."""

import os

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ModelFallbackMiddleware,
    SummarizationMiddleware,
)
from sentinel.checkpoint import create_checkpointer

from sentinel.config import model, _create_model, _PROVIDER_FALLBACK_DEFAULTS
from sentinel.prompts import SENTINEL_SYSTEM_PROMPT
from sentinel.subagents import all_subagents
from sentinel.tools import all_tools

REPORTS_DIR = os.environ.get("SENTINEL_REPORTS_DIR", "./reports")
SKILLS_DIR = os.environ.get("SENTINEL_SKILLS_DIR", "./skills/")
RUN_LIMIT = int(os.environ.get("SENTINEL_RUN_LIMIT", "30"))
FALLBACK_MODEL_NAME = os.environ.get("SENTINEL_FALLBACK_MODEL", "")


def _get_fallback_model():
    """현재 프로바이더에 맞는 폴백 모델을 생성합니다.

    SENTINEL_FALLBACK_MODEL이 설정되면 그대로 사용하고,
    없으면 프로바이더별 기본 fallback을 적용합니다.
    """
    provider = os.environ.get("SENTINEL_PROVIDER", "openai").lower()
    fallback_name = FALLBACK_MODEL_NAME or _PROVIDER_FALLBACK_DEFAULTS.get(
        provider, "gpt-4.1-mini"
    )
    return _create_model(model=fallback_name)


def create_sentinel_agent():
    """Sentinel LLMOps 에이전트를 생성합니다."""
    fallback = _get_fallback_model()
    return create_deep_agent(
        model=model,
        tools=all_tools,
        subagents=all_subagents,
        system_prompt=SENTINEL_SYSTEM_PROMPT,
        backend=FilesystemBackend(root_dir=REPORTS_DIR, virtual_mode=True),
        skills=[SKILLS_DIR],
        checkpointer=create_checkpointer(),
        middleware=[
            SummarizationMiddleware(model=model, trigger=("messages", 15)),
            ModelCallLimitMiddleware(run_limit=RUN_LIMIT),
            ModelFallbackMiddleware(fallback),
        ],
    )
