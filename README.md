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
├── server.py                    # FastAPI 웹 서버 엔트리포인트
├── pyproject.toml
├── sentinel/
│   ├── agent.py                 # create_sentinel_agent()
│   ├── config.py                # 멀티 프로바이더 모델 팩토리, Langfuse 클라이언트
│   ├── prompts.py               # Sentinel 시스템 프롬프트
│   ├── subagents.py             # 서브에이전트 3개
│   ├── report_template.html     # McKinsey 스타일 A4 HTML 템플릿
│   ├── tools/
│   │   ├── traces.py            # list_traces, get_trace_detail, list_sessions
│   │   ├── prompt_mgmt.py       # get/save_langfuse_prompt, suggest_prompt_improvement
│   │   ├── evaluation.py        # evaluate_with_llm, list_scores, create_score
│   │   ├── metrics.py           # query_metrics, generate_report
│   │   └── platform.py          # manage_datasets, manage_annotations, think_tool
│   ├── web/
│   │   ├── app.py               # FastAPI 앱 팩토리
│   │   ├── routes.py            # 웹 페이지 + API 라우트
│   │   ├── scheduler.py         # APScheduler 크론 잡
│   │   └── notify.py            # Slack / Telegram / Email 알림
│   └── templates/
│       ├── base.html            # Jinja2 + Tailwind 베이스
│       ├── index.html           # 대시보드
│       ├── reports.html         # 보고서 목록 + 생성
│       └── report_view.html     # 보고서 상세 보기
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
# CLI 대화형 모드
python main.py

# CLI 단일 질의
python main.py --query "최근 3일간 트레이스를 분석해주세요"

# 웹 서버 (대시보드 + 스케줄러)
python server.py
```

## 웹 서버

`python server.py`로 FastAPI 서버를 실행하면:

- **대시보드** (`/`) — 보고서 현황 + 즉시 생성 폼
- **보고서 목록** (`/reports`) — 전체 보고서 조회, 다운로드
- **보고서 상세** (`/reports/{filename}`) — MD/HTML 보고서 보기
- **스케줄러 상태** (`/api/scheduler/status`) — 크론 잡 현황

### 자동 보고서 스케줄러

| 주기 | 실행 시각 | 보고서 범위 |
|------|----------|-----------|
| 일간 | 매일 00:00 | 전일 (00:00~23:59) |
| 주간 | 매주 월요일 00:00 | 지난주 월~일 |
| 월간 | 매월 1일 00:00 | 지난달 전체 |

### 알림 채널

보고서 생성 시 설정된 채널로 자동 전송합니다.

| 채널 | 필요 환경변수 |
|------|-------------|
| Slack | `SENTINEL_SLACK_WEBHOOK` |
| Telegram | `SENTINEL_TELEGRAM_BOT_TOKEN`, `SENTINEL_TELEGRAM_CHAT_ID` |
| Email (SMTP) | `SENTINEL_SMTP_HOST`, `SENTINEL_SMTP_USER`, `SENTINEL_SMTP_PASS`, `SENTINEL_EMAIL_TO` |

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

## 보고서

`generate_report` 도구는 Markdown 보고서를 항상 생성하며, HTML은 옵션입니다.

- **MD** (기본): McKinsey 컨설팅 스타일 구조화된 보고서
- **HTML** (`output_html=True`): A4 인쇄 대응 HTML 보고서

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
| `SENTINEL_REPORTS_DIR` | — | `./reports` | 보고서 저장 경로 |
| `SENTINEL_RUN_LIMIT` | — | `30` | 최대 모델 호출 수 |
| `SENTINEL_AUTO_HTML` | — | `true` | 스케줄러 HTML 자동 생성 |
| `SENTINEL_SLACK_WEBHOOK` | — | — | Slack Incoming Webhook URL |
| `SENTINEL_TELEGRAM_BOT_TOKEN` | — | — | Telegram Bot 토큰 |
| `SENTINEL_TELEGRAM_CHAT_ID` | — | — | Telegram Chat ID |
| `SENTINEL_SMTP_HOST` | — | — | SMTP 서버 호스트 |
| `SENTINEL_SMTP_USER` | — | — | SMTP 로그인 사용자 |
| `SENTINEL_SMTP_PASS` | — | — | SMTP 비밀번호 |
| `SENTINEL_EMAIL_TO` | — | — | 보고서 수신 이메일 |

## 기술 스택

- [Deep Agents](https://deepagents.ai) — 에이전트 프레임워크
- [LangChain](https://python.langchain.com) — LLM 추상화, 도구 정의
- [LangGraph](https://langchain-ai.github.io/langgraph) — 상태 관리, 체크포인팅
- [Langfuse](https://langfuse.com) — LLM 관측성 플랫폼
- [FastAPI](https://fastapi.tiangolo.com) — 웹 서버
- [APScheduler](https://apscheduler.readthedocs.io) — 크론 스케줄러

## 라이선스

MIT
