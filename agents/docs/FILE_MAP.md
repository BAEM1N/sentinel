# Sentinel File Map

## Project Root (`D:\sentinel\`)

```
sentinel/
├── .env                          # 실제 환경 변수 (gitignore)
├── .env.example                  # 환경 변수 템플릿 (9 프로바이더 + 알림)
├── .gitignore                    # reports/*.md, *.html, .env, .venv 등
├── pyproject.toml                # 프로젝트 메타 + 의존성 + scripts
├── README.md                     # 사용법, 아키텍처, 환경변수 문서
├── main.py                       # CLI 엔트리포인트 (대화형/단일질의)
├── server.py                     # FastAPI 서버 엔트리포인트
├── reports/                      # 생성된 보고서 저장 (gitignore)
│   ├── daily_report.md
│   ├── weekly_report.md
│   ├── monthly_report.md
│   └── *.html
├── skills/
│   └── langfuse-ops/
│       └── SKILL.md              # Langfuse LLMOps 스킬 정의 + API 레퍼런스
├── agents/
│   └── docs/                     # 이 문서들 (Claude 세션 간 컨텍스트 전달용)
└── sentinel/                     # 메인 패키지
    ├── __init__.py
    ├── config.py                 # 모델 팩토리, Langfuse 클라이언트, 콜백
    ├── agent.py                  # create_sentinel_agent() — 에이전트 조립
    ├── prompts.py                # SENTINEL_SYSTEM_PROMPT
    ├── subagents.py              # 3 서브에이전트 정의
    ├── report_template.html      # McKinsey A4 HTML 보고서 템플릿
    ├── tools/
    │   ├── __init__.py           # all_tools 리스트 (14개)
    │   ├── traces.py             # list_traces, get_trace_detail, list_sessions
    │   ├── prompt_mgmt.py        # get/save_langfuse_prompt, suggest_prompt_improvement
    │   ├── evaluation.py         # list_scores, create_score, evaluate_with_llm
    │   ├── metrics.py            # query_metrics, generate_report + MD/HTML 프롬프트
    │   └── platform.py           # manage_datasets, manage_annotations, think_tool
    ├── templates/
    │   ├── base.html             # 공통 레이아웃 (Pretendard, Tailwind, nav)
    │   ├── index.html            # 대시보드 페이지
    │   ├── reports.html          # 보고서 목록 페이지
    │   ├── report_view.html      # 보고서 상세 뷰 (marked.js)
    │   └── scheduler.html        # 스케줄러 상태 페이지
    └── web/
        ├── __init__.py
        ├── app.py                # FastAPI 앱 팩토리 + lifespan
        ├── routes.py             # 모든 라우트 (페이지 + API)
        ├── scheduler.py          # APScheduler 크론 잡
        └── notify.py             # Slack/Telegram/Email 알림
```

## Entry Points

| 명령 | 파일 | 설명 |
|------|------|------|
| `python main.py` | `main.py` | CLI 대화형 모드 |
| `python main.py -q "..."` | `main.py` | CLI 단일 질의 |
| `python server.py` | `server.py` | FastAPI 개발 서버 (uvicorn reload) |
| `uvicorn server:app` | `server.py` | 프로덕션 서버 |

## Route Map

| Method | Path | Handler | 설명 |
|--------|------|---------|------|
| GET | `/` | `page_index` | 대시보드 |
| GET | `/reports` | `page_reports` | 보고서 목록 |
| GET | `/reports/{filename}` | `page_report_view` | 보고서 상세 |
| GET | `/reports/{filename}/raw` | `download_report` | 보고서 다운로드 |
| GET | `/scheduler` | `page_scheduler` | 스케줄러 페이지 |
| POST | `/api/generate` | `api_generate` | 보고서 생성 |
| GET | `/api/scheduler/status` | `scheduler_status` | 스케줄러 상태 JSON |

## Tool Inventory (14개)

| # | 도구 | 파일 | 용도 |
|---|------|------|------|
| 1 | `list_traces` | traces.py | 트레이스 필터 조회 |
| 2 | `get_trace_detail` | traces.py | 단일 트레이스 상세 |
| 3 | `list_sessions` | traces.py | 세션 목록 |
| 4 | `get_langfuse_prompt` | prompt_mgmt.py | 프롬프트 조회 |
| 5 | `save_langfuse_prompt` | prompt_mgmt.py | 프롬프트 저장 |
| 6 | `suggest_prompt_improvement` | prompt_mgmt.py | 프롬프트 개선안 |
| 7 | `list_scores` | evaluation.py | 스코어 조회 |
| 8 | `create_score` | evaluation.py | 스코어 생성 |
| 9 | `evaluate_with_llm` | evaluation.py | LLM-as-judge |
| 10 | `query_metrics` | metrics.py | Metrics API 집계 |
| 11 | `generate_report` | metrics.py | 보고서 생성 |
| 12 | `manage_datasets` | platform.py | 데이터셋 CRUD |
| 13 | `manage_annotations` | platform.py | 주석/코멘트 |
| 14 | `think_tool` | platform.py | 전략적 반성 |
