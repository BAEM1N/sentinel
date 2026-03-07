# Sentinel

**Langfuse 기반 LLMOps 에이전트** — Deep Agents 프레임워크로 구축된 LLM 애플리케이션 운영 자동화 도구입니다.

트레이스 분석, 프롬프트 버전 관리, LLM-as-judge 자동 평가, 운영 보고서 생성, 플랫폼 데이터 관리를 하나의 대화형 에이전트로 수행합니다.

## 주요 기능

| 영역 | 기능 | 설명 |
|------|------|------|
| **Observe** | 트레이스 조회 | user, session, 날짜, 태그 등 다중 필터 지원 |
| | 세션 조회 | 세션 단위 트레이스 그룹 분석 |
| | Metrics 집계 | Langfuse Metrics API로 비용/레이턴시/토큰 집계 |
| **Analyze** | 트레이스 상세 분석 | observation, 스코어, 입출력, 메타데이터 드릴다운 |
| | 전략적 반성 | think_tool로 분석 전략 수립 |
| **Act** | 프롬프트 관리 | 버전/라벨별 조회, 신규 버전 생성, 데이터 기반 개선안 |
| | 자동 평가 | LLM-as-judge로 품질 평가 후 스코어 자동 기록 |
| | 스코어 관리 | 수동 스코어 생성/조회 |
| **Report** | 보고서 생성 | 일간/주간/월간 McKinsey 스타일 보고서 (MD 기본 + HTML 옵션) |
| | 데이터셋 관리 | 평가용 데이터셋 생성, 아이템 추가/조회 |
| | 주석 관리 | 트레이스에 코멘트(리뷰 주석) 작성 |

## 아키텍처

```
sentinel/
├── main.py                      # CLI 엔트리포인트 (대화형 / 단일 질의)
├── pyproject.toml
├── sentinel/
│   ├── agent.py                 # create_sentinel_agent()
│   ├── config.py                # 멀티 프로바이더 모델 팩토리, Langfuse 클라이언트
│   ├── prompts.py               # Sentinel 시스템 프롬프트
│   ├── subagents.py             # 서브에이전트 3개
│   ├── report_template.html     # McKinsey 스타일 A4 HTML 템플릿
│   └── tools/
│       ├── traces.py            # list_traces, get_trace_detail, list_sessions
│       ├── prompt_mgmt.py       # get/save_langfuse_prompt, suggest_prompt_improvement
│       ├── evaluation.py        # evaluate_with_llm, list_scores, create_score
│       ├── metrics.py           # query_metrics, generate_report
│       └── platform.py          # manage_datasets, manage_annotations, think_tool
├── skills/
│   └── langfuse-ops/SKILL.md    # Langfuse SDK API 레퍼런스 (에이전트용)
└── reports/                     # 보고서 출력 디렉토리
```

## 빠른 시작

### 1. 환경 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 API 키를 설정합니다
```

### 2. 의존성 설치

```bash
# 기본 (OpenAI만)
pip install -e .

# 특정 프로바이더 추가
pip install -e ".[anthropic]"
pip install -e ".[gemini]"
pip install -e ".[ollama]"

# 전체 프로바이더
pip install -e ".[all-providers]"
```

### 3. 실행

```bash
# 대화형 모드
python main.py

# 단일 질의
python main.py --query "최근 3일간 트레이스를 분석해주세요"

# 보고서 생성
python main.py -q "주간 LLMOps 보고서를 생성해주세요"
```

## 멀티 프로바이더

`.env`에서 `SENTINEL_PROVIDER`를 설정하여 LLM 프로바이더를 변경할 수 있습니다.

| 프로바이더 | 패키지 | 모델 기본값 | 필요 환경변수 |
|-----------|--------|-----------|-------------|
| `openai` (기본) | langchain-openai | gpt-5.4 | `OPENAI_API_KEY` |
| `anthropic` | langchain-anthropic | claude-sonnet-4-6 | `ANTHROPIC_API_KEY` |
| `gemini` | langchain-google-genai | gemini-2.5-flash | `GOOGLE_API_KEY` |
| `ollama` | langchain-ollama | llama3.1 | — (로컬) |
| `vllm` | langchain-openai | Llama-3.1-70B | — (로컬) |
| `lmstudio` | langchain-openai | local-model | — (로컬) |
| `openrouter` | langchain-openai | claude-sonnet-4-6 | `OPENROUTER_API_KEY` |
| `qwen` | langchain-openai | qwen-max | `DASHSCOPE_API_KEY` |
| `glm` | langchain-openai | glm-4-plus | `GLM_API_KEY` |

```env
# Anthropic 사용 예시
SENTINEL_PROVIDER=anthropic
SENTINEL_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...
```

## 보고서

`generate_report` 도구는 Markdown 보고서를 항상 생성하며, HTML은 옵션입니다.

- **MD** (기본): McKinsey 컨설팅 스타일 구조화된 보고서
- **HTML** (`output_html=True`): A4 인쇄 대응 HTML 보고서

```
python main.py -q "주간 보고서를 HTML로도 생성해주세요"
```

## 환경 변수

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `OPENAI_API_KEY` | O | — | OpenAI API 키 |
| `LANGFUSE_SECRET_KEY` | O | — | Langfuse Secret 키 |
| `LANGFUSE_PUBLIC_KEY` | O | — | Langfuse Public 키 |
| `LANGFUSE_HOST` | O | — | Langfuse 호스트 URL |
| `SENTINEL_PROVIDER` | — | `openai` | LLM 프로바이더 |
| `SENTINEL_MODEL` | — | 프로바이더별 기본값 | LLM 모델명 |
| `SENTINEL_FALLBACK_MODEL` | — | `gpt-5.3-instant` | 폴백 모델 |
| `SENTINEL_BASE_URL` | — | — | OpenAI 호환 프로바이더 엔드포인트 |
| `SENTINEL_API_KEY` | — | — | 프로바이더 공통 API 키 |
| `SENTINEL_REPORTS_DIR` | — | `./reports` | 보고서 저장 경로 |
| `SENTINEL_RUN_LIMIT` | — | `30` | 최대 모델 호출 수 |

## 기술 스택

- [Deep Agents](https://deepagents.ai) — 에이전트 프레임워크 (서브에이전트, 스킬, 백엔드)
- [LangChain](https://python.langchain.com) — LLM 추상화, 도구 정의
- [LangGraph](https://langchain-ai.github.io/langgraph) — 상태 관리, 체크포인팅
- [Langfuse](https://langfuse.com) — LLM 관측성 플랫폼

## 라이선스

MIT
