# Sentinel Architecture

## Overview

Sentinel은 **Langfuse 기반 LLMOps 에이전트**이다. Deep Agents 프레임워크 위에 구축되어 LLM 애플리케이션의 관측성, 프롬프트 관리, 품질 평가, 자동 보고서 생성을 수행한다.

## System Diagram

```
                          +--------------------------+
                          |     FastAPI Server       |
                          |   (server.py → web/)     |
                          +----+--------+-----+------+
                               |        |     |
                    +----------+  +-----+  +--+----------+
                    |             |         |             |
               Web UI        REST API   APScheduler
           (Jinja2+TW)    (/api/*)    (cron jobs)
                    |             |         |
                    +------+------+---------+
                           |
                    +------+------+
                    |   Agent     |
                    | (agent.py)  |
                    +------+------+
                           |
              +------------+------------+
              |            |            |
        14 Tools    3 Subagents    Skill
        (tools/)   (subagents.py) (SKILL.md)
              |            |            |
              +------+-----+-----+-----+
                     |           |
               Langfuse API   LLM Provider
              (lf_client)    (_create_model)
```

## Core Components

### 1. Agent Layer (`sentinel/agent.py`)
- `create_deep_agent()` 호출로 에이전트 생성
- 14개 커스텀 도구 + 3개 서브에이전트 구성
- `FilesystemBackend` — 보고서 파일 저장
- `InMemorySaver` — 체크포인터 (대화 상태 유지)
- Middleware 3종:
  - `SummarizationMiddleware` — 15 메시지 초과 시 자동 요약
  - `ModelCallLimitMiddleware` — 최대 호출 수 제한 (기본 30)
  - `ModelFallbackMiddleware` — 1차 모델 실패 시 폴백 모델 사용

### 2. Config Layer (`sentinel/config.py`)
- 멀티 프로바이더 LLM 모델 팩토리 (`_create_model()`)
- 지원 프로바이더 9종: openai, anthropic, gemini, ollama, vllm, lmstudio, openrouter, qwen, glm
- 모듈 레벨 `model` 인스턴스 — 전역 공유
- Langfuse 클라이언트 (`lf_client`) 및 콜백 핸들러 초기화

### 3. Tools Layer (`sentinel/tools/`)
| 파일 | 도구 | 설명 |
|------|------|------|
| `traces.py` | `list_traces`, `get_trace_detail`, `list_sessions` | 트레이스/세션 조회 |
| `prompt_mgmt.py` | `get_langfuse_prompt`, `save_langfuse_prompt`, `suggest_prompt_improvement` | 프롬프트 CRUD + 개선 |
| `evaluation.py` | `list_scores`, `create_score`, `evaluate_with_llm` | LLM-as-judge 평가 |
| `metrics.py` | `query_metrics`, `generate_report` | Metrics API 집계 + 보고서 생성 |
| `platform.py` | `manage_datasets`, `manage_annotations`, `think_tool` | 데이터셋/주석 관리 |

### 4. Subagents (`sentinel/subagents.py`)
| 서브에이전트 | 역할 |
|-------------|------|
| `trace-analyst` | 트레이스 데이터 심층 분석, 성능 병목/에러 패턴/비용 이상 발견 |
| `prompt-optimizer` | 프롬프트 분석 → 트레이스 기반 개선안 → staging 저장 |
| `quality-evaluator` | LLM-as-judge 자동 평가 → 품질 트렌드 → 보고서 |

### 5. Web Layer (`sentinel/web/`)
| 파일 | 역할 |
|------|------|
| `app.py` | FastAPI 앱 팩토리, lifespan (스케줄러 시작/종료) |
| `routes.py` | 페이지 라우트 (`/`, `/reports`, `/reports/{name}`, `/scheduler`) + API (`/api/generate`, `/api/scheduler/status`) |
| `scheduler.py` | APScheduler 크론 잡 3종 (daily/weekly/monthly) |
| `notify.py` | 알림 전송 (Slack webhook, Telegram Bot, SMTP email) |

### 6. Templates (`sentinel/templates/`)
| 파일 | 역할 |
|------|------|
| `base.html` | 공통 레이아웃 (Pretendard, Tailwind, nav, footer) |
| `index.html` | 대시보드 — KPI 스트립 + 생성 폼 + 최근 보고서 |
| `reports.html` | 보고서 목록 — 아코디언 생성 폼 + 전체 테이블 |
| `report_view.html` | 보고서 뷰어 — marked.js MD 렌더링 |
| `scheduler.html` | 스케줄러 상태 — 잡 목록 + 스케줄 요약 |

### 7. Report Template (`sentinel/report_template.html`)
- McKinsey 스타일 A4 HTML 보고서 템플릿
- Pretendard 폰트, 모노크롬 디자인
- `{{content}}`, `{{title}}`, `{{generated_at}}` 플레이스홀더

## Data Flow

### 보고서 생성 플로우
```
1. 요청 (CLI / Web UI / Scheduler)
2. _collect_report_data() → Langfuse API 호출
   - Metrics API (traces view, 집계)
   - Trace API (최근 30건 상세)
   - Score API (평가 스코어)
3. REPORT_MD_PROMPT에 데이터 삽입 → LLM 호출 → MD 보고서 생성
4. (옵션) REPORT_HTML_PROMPT → LLM → HTML body → report_template.html 삽입
5. 파일 저장 (reports/ 디렉토리)
6. (설정 시) send_report() → Slack/Telegram/Email 알림
```

### 스케줄러 플로우
```
daily  → 매일 00:00 → 전일 (어제 00:00~23:59) 보고서
weekly → 매주 월 00:00 → 지난주 (월~일) 보고서
monthly → 매월 1일 00:00 → 지난달 보고서
```

## Environment Variables

### 필수
| 변수 | 설명 |
|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 (기본 프로바이더) |
| `LANGFUSE_SECRET_KEY` | Langfuse Secret Key |
| `LANGFUSE_PUBLIC_KEY` | Langfuse Public Key |
| `LANGFUSE_HOST` | Langfuse 호스트 URL |

### 모델 설정
| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SENTINEL_PROVIDER` | `openai` | LLM 프로바이더 |
| `SENTINEL_MODEL` | 프로바이더별 기본값 | 모델명 |
| `SENTINEL_BASE_URL` | 프로바이더별 기본값 | OpenAI 호환 엔드포인트 |
| `SENTINEL_API_KEY` | - | 프로바이더 공통 API 키 |
| `SENTINEL_FALLBACK_MODEL` | `gpt-5.3-instant` | 폴백 모델명 |

### 에이전트 설정
| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SENTINEL_REPORTS_DIR` | `./reports` | 보고서 저장 디렉토리 |
| `SENTINEL_SKILLS_DIR` | `./skills/` | 스킬 디렉토리 |
| `SENTINEL_RUN_LIMIT` | `30` | 모델 호출 제한 |
| `SENTINEL_AUTO_HTML` | `true` | 스케줄러 HTML 자동 생성 |

### 알림 설정
| 변수 | 설명 |
|------|------|
| `SENTINEL_SLACK_WEBHOOK` | Slack Incoming Webhook URL |
| `SENTINEL_TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `SENTINEL_TELEGRAM_CHAT_ID` | Telegram Chat ID |
| `SENTINEL_SMTP_HOST` | SMTP 호스트 |
| `SENTINEL_SMTP_PORT` | SMTP 포트 (기본 587) |
| `SENTINEL_SMTP_USER` | SMTP 사용자 |
| `SENTINEL_SMTP_PASS` | SMTP 비밀번호 |
| `SENTINEL_EMAIL_TO` | 수신 이메일 |
| `SENTINEL_EMAIL_FROM` | 발신 이메일 |

## Dependencies

### Core (pyproject.toml)
```
deepagents>=0.4.4
langchain>=1.2
langchain-openai>=1.1.10
langfuse>=2.0
langgraph>=1.0
python-dotenv>=1.2.2
fastapi>=0.115
uvicorn[standard]>=0.34
jinja2>=3.1
apscheduler>=3.10
httpx>=0.28
```

### Optional Providers
```
[anthropic] langchain-anthropic>=0.3
[gemini]    langchain-google-genai>=2.1
[ollama]    langchain-ollama>=0.3
[all-providers] 위 세 개 전부
```
