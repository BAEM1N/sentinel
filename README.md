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
| **Report** | 보고서 생성 | 일간/주간/월간 LLMOps 마크다운 보고서 |
| | 데이터셋 관리 | 평가용 데이터셋 생성, 아이템 추가/조회 |
| | 주석 관리 | 트레이스에 코멘트(리뷰 주석) 작성 |

## 아키텍처

```
sentinel/
├── main.py                      # CLI 엔트리포인트 (대화형 / 단일 질의)
├── pyproject.toml
├── sentinel/
│   ├── agent.py                 # create_sentinel_agent()
│   ├── config.py                # 모델, Langfuse 클라이언트, 콜백
│   ├── prompts.py               # Sentinel 시스템 프롬프트
│   ├── subagents.py             # 서브에이전트 3개
│   └── tools/
│       ├── traces.py            # list_traces, get_trace_detail, list_sessions
│       ├── prompt_mgmt.py       # get/save_langfuse_prompt, suggest_prompt_improvement
│       ├── evaluation.py        # evaluate_with_llm, list_scores, create_score
│       ├── metrics.py           # query_metrics, generate_report
│       └── platform.py         # manage_datasets, manage_annotations, think_tool
├── skills/
│   └── langfuse-ops/SKILL.md    # Langfuse SDK API 레퍼런스 (에이전트용)
└── reports/                     # 보고서 출력 디렉토리
```

### 서브에이전트

메인 에이전트가 복잡한 작업을 3개의 전문 서브에이전트에게 위임합니다:

| 서브에이전트 | 역할 | 담당 도구 |
|------------|------|----------|
| **trace-analyst** | 성능 병목, 에러 패턴, 비용 이상 탐지 | list_traces, get_trace_detail, list_sessions, query_metrics |
| **prompt-optimizer** | 프롬프트 조회, 저품질 응답 분석, 개선안 생성 | get/save_langfuse_prompt, suggest_prompt_improvement |
| **quality-evaluator** | LLM-as-judge 평가 실행, 품질 트렌드 분석 | evaluate_with_llm, list_scores, generate_report |

### 미들웨어

| 미들웨어 | 역할 |
|---------|------|
| SummarizationMiddleware | 긴 대화 자동 요약으로 컨텍스트 절약 |
| ModelCallLimitMiddleware | 무한 루프 방지 (기본 30회 제한) |
| ModelFallbackMiddleware | 주 모델 실패 시 폴백 모델로 전환 |

## 빠른 시작

### 1. 환경 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 API 키를 설정합니다
```

```env
# 필수
OPENAI_API_KEY=sk-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 2. 의존성 설치

```bash
pip install -e .
# 또는
uv pip install -e .
```

### 3. 실행

```bash
# 대화형 모드
python main.py

# 단일 질의
python main.py --query "최근 3일간 트레이스를 분석해주세요"

# 보고서 생성
python main.py -q "주간 LLMOps 보고서를 생성해서 reports/weekly.md로 저장해주세요"
```

## 사용 예시

### 트레이스 분석

```
[You] 최근 일주일간 에러가 많은 트레이스 패턴을 찾고, 사용자별 비용을 분석해주세요

[Sentinel]
trace-analyst에게 분석을 위임합니다...

## 핵심 발견
| 사용자     | 트레이스 수 | 에러 수 | 총 비용   |
|-----------|-----------|--------|----------|
| user-101  | 142       | 12     | $3.45    |
| user-205  | 89        | 1      | $1.82    |

- user-101에서 timeout 에러가 집중 발생 (8/12건)
- 평균 레이턴시 4.2초로 SLA 초과

## 권장 조치
1. user-101 워크로드의 max_tokens 제한 검토
2. timeout 임계값 상향 조정 (3s → 5s)
```

### 프롬프트 개선

```
[You] rag-agent 프롬프트를 분석하고 개선해주세요

[Sentinel]
prompt-optimizer에게 위임합니다...

## Before (v3, production)
"당신은 RAG 에이전트입니다..."

## After (v4, staging)
"당신은 RAG 에이전트입니다...
  + 검색 결과가 없는 경우 '정보를 찾을 수 없습니다'로 응답
  + 출처를 [문서명:페이지] 형식으로 명시"

staging 라벨로 저장 완료. A/B 테스트 후 production 승격을 권장합니다.
```

### 자동 평가 + 보고서

```
[You] 최근 트레이스 10개를 평가하고 주간 보고서를 생성해주세요

[Sentinel]
quality-evaluator에게 위임합니다...

- 10개 트레이스 LLM-as-judge 평가 완료
- 평균 종합점수: 0.78 (정확성 4.1, 완전성 3.8, 유용성 4.0)
- 주간 보고서 → reports/weekly_report.md 저장 완료
```

## 환경 변수 (전체)

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `OPENAI_API_KEY` | O | — | OpenAI API 키 |
| `LANGFUSE_SECRET_KEY` | O | — | Langfuse Secret 키 |
| `LANGFUSE_PUBLIC_KEY` | O | — | Langfuse Public 키 |
| `LANGFUSE_HOST` | O | — | Langfuse 호스트 URL |
| `SENTINEL_MODEL` | — | `gpt-4.1` | 기본 LLM 모델 |
| `SENTINEL_FALLBACK_MODEL` | — | `gpt-4.1-mini` | 폴백 모델 |
| `SENTINEL_REPORTS_DIR` | — | `./reports` | 보고서 저장 경로 |
| `SENTINEL_SKILLS_DIR` | — | `./skills/` | 스킬 디렉토리 경로 |
| `SENTINEL_RUN_LIMIT` | — | `30` | 최대 모델 호출 수 |

## 기술 스택

- [Deep Agents](https://deepagents.ai) — 에이전트 프레임워크 (서브에이전트, 스킬, 백엔드)
- [LangChain](https://python.langchain.com) — LLM 추상화, 도구 정의
- [LangGraph](https://langchain-ai.github.io/langgraph) — 상태 관리, 체크포인팅
- [Langfuse](https://langfuse.com) — LLM 관측성 플랫폼 (트레이스, 프롬프트, 스코어, Metrics API)

## 라이선스

MIT
