"""Sentinel 에이전트 생성."""

import os

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ModelFallbackMiddleware,
    SummarizationMiddleware,
)
from langgraph.checkpoint.memory import InMemorySaver

from sentinel.config import model, _create_model
from sentinel.prompts import SENTINEL_SYSTEM_PROMPT
from sentinel.subagents import all_subagents
from sentinel.tools import all_tools

REPORTS_DIR = os.environ.get("SENTINEL_REPORTS_DIR", "./reports")
SKILLS_DIR = os.environ.get("SENTINEL_SKILLS_DIR", "./skills/")
RUN_LIMIT = int(os.environ.get("SENTINEL_RUN_LIMIT", "30"))
FALLBACK_MODEL_NAME = os.environ.get("SENTINEL_FALLBACK_MODEL", "gpt-5.3-instant")


def _get_fallback_model():
    """현재 프로바이더에 맞는 폴백 모델을 생성합니다."""
    return _create_model(model=FALLBACK_MODEL_NAME)


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
        checkpointer=InMemorySaver(),
        middleware=[
            SummarizationMiddleware(model=model, trigger=("messages", 15)),
            ModelCallLimitMiddleware(run_limit=RUN_LIMIT),
            ModelFallbackMiddleware(fallback),
        ],
    )
