"""설정 모듈 — 멀티 프로바이더 모델, Langfuse 클라이언트, 콜백 초기화.

지원 프로바이더:
  - openai      : ChatOpenAI (기본)
  - anthropic   : ChatAnthropic (langchain-anthropic)
  - gemini      : ChatGoogleGenerativeAI (langchain-google-genai)
  - ollama      : ChatOllama (langchain-ollama)
  - vllm        : ChatOpenAI + base_url (OpenAI 호환)
  - lmstudio    : ChatOpenAI + base_url (OpenAI 호환)
  - openrouter  : ChatOpenAI + base_url (OpenAI 호환)
  - qwen        : ChatOpenAI + base_url (OpenAI 호환)
  - glm         : ChatOpenAI + base_url (OpenAI 호환)

환경변수:
  SENTINEL_PROVIDER  : 프로바이더 이름 (기본: openai)
  SENTINEL_MODEL     : 모델명 (기본: 프로바이더별 기본값)
  SENTINEL_BASE_URL  : OpenAI 호환 프로바이더의 커스텀 엔드포인트
  SENTINEL_API_KEY   : 프로바이더 API 키 (없으면 프로바이더별 기본 env var 사용)
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# 프로바이더별 기본 설정
# ---------------------------------------------------------------------------

_PROVIDER_DEFAULTS: dict[str, dict] = {
    "openai": {
        "model": "gpt-5.4",
        "env_key": "OPENAI_API_KEY",
    },
    "anthropic": {
        "model": "claude-sonnet-4-6",
        "env_key": "ANTHROPIC_API_KEY",
    },
    "gemini": {
        "model": "gemini-2.5-flash",
        "env_key": "GOOGLE_API_KEY",
    },
    "ollama": {
        "model": "llama3.1",
        "base_url": "http://localhost:11434",
    },
    "vllm": {
        "model": "meta-llama/Llama-3.1-70B-Instruct",
        "base_url": "http://localhost:8000/v1",
        "env_key": "VLLM_API_KEY",
    },
    "lmstudio": {
        "model": "local-model",
        "base_url": "http://localhost:1234/v1",
    },
    "openrouter": {
        "model": "anthropic/claude-sonnet-4-6",
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
    },
    "qwen": {
        "model": "qwen-max",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "env_key": "DASHSCOPE_API_KEY",
    },
    "glm": {
        "model": "glm-4-plus",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "env_key": "GLM_API_KEY",
    },
}

# OpenAI 호환 API를 사용하는 프로바이더 (ChatOpenAI + base_url)
_OPENAI_COMPAT_PROVIDERS = {"vllm", "lmstudio", "openrouter", "qwen", "glm"}


# ---------------------------------------------------------------------------
# 모델 팩토리
# ---------------------------------------------------------------------------

def _create_model(provider: str | None = None, model: str | None = None):
    """프로바이더에 맞는 LangChain ChatModel을 생성합니다."""
    provider = (provider or os.environ.get("SENTINEL_PROVIDER", "openai")).lower()
    defaults = _PROVIDER_DEFAULTS.get(provider, _PROVIDER_DEFAULTS["openai"])
    model_name = model or os.environ.get("SENTINEL_MODEL", defaults["model"])

    # API 키
    api_key = os.environ.get("SENTINEL_API_KEY") or os.environ.get(
        defaults.get("env_key", ""), ""
    )
    # 베이스 URL
    base_url = os.environ.get("SENTINEL_BASE_URL", defaults.get("base_url", ""))

    # --- 네이티브 프로바이더 ---
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        kwargs = {"model": model_name}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOpenAI(**kwargs)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        kwargs = {"model": model_name}
        if api_key:
            kwargs["api_key"] = api_key
        return ChatAnthropic(**kwargs)

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        kwargs = {"model": model_name}
        if api_key:
            kwargs["google_api_key"] = api_key
        return ChatGoogleGenerativeAI(**kwargs)

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        kwargs = {"model": model_name}
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOllama(**kwargs)

    # --- OpenAI 호환 프로바이더 ---
    if provider in _OPENAI_COMPAT_PROVIDERS:
        from langchain_openai import ChatOpenAI
        kwargs = {"model": model_name, "base_url": base_url}
        if api_key:
            kwargs["api_key"] = api_key
        elif provider == "lmstudio":
            kwargs["api_key"] = "lm-studio"  # LM Studio는 키 불필요
        return ChatOpenAI(**kwargs)

    raise ValueError(
        f"지원하지 않는 프로바이더: '{provider}'. "
        f"사용 가능: {', '.join(sorted(_PROVIDER_DEFAULTS.keys()))}"
    )


# ---------------------------------------------------------------------------
# 모듈 레벨 인스턴스
# ---------------------------------------------------------------------------

model = _create_model()

# --- Langfuse 클라이언트 ---
from langfuse import Langfuse  # noqa: E402

lf_client = Langfuse()

# --- 콜백 (observability) ---
langfuse_handler = None
if os.environ.get("LANGFUSE_SECRET_KEY"):
    try:
        from langfuse.langchain import CallbackHandler  # noqa: E402
        langfuse_handler = CallbackHandler()
    except (ImportError, ModuleNotFoundError):
        pass

lf_config: dict = {"callbacks": [langfuse_handler]} if langfuse_handler else {}
