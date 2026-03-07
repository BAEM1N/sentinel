---
name: langfuse-ops
description: >
  Langfuse LLMOps 운영 가이드. 트레이스/세션 조회, Metrics API 집계,
  프롬프트 버전 관리, LLM-as-judge 평가, 일간/주간 보고서 생성,
  데이터셋·주석·모델 관리를 포함합니다.
license: MIT
compatibility: Python 3.12+
metadata:
  category: llmops
  difficulty: advanced
allowed-tools:
  - list_traces
  - get_trace_detail
  - list_sessions
  - get_langfuse_prompt
  - save_langfuse_prompt
  - list_scores
  - create_score
  - evaluate_with_llm
  - query_metrics
  - generate_report
  - manage_datasets
  - manage_annotations
  - think_tool
  - write_todos
  - task
  - write_file
---

# Langfuse LLMOps 스킬

## 사용 시기
- LLM 애플리케이션의 트레이스를 조회·분석할 때
- 프롬프트를 버전 관리하고 데이터 기반으로 개선할 때
- LLM-as-judge 자동 평가를 실행할 때
- 일간·주간·월간 LLMOps 보고서를 생성할 때
- Langfuse 프로젝트 데이터셋, 주석, 모델을 관리할 때

---

## Langfuse Python SDK API 레퍼런스

### 클라이언트 초기화
```python
from langfuse import Langfuse
lf = Langfuse()  # .env에서 LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_HOST 자동 로드
```

### 1. 트레이스 API

#### 트레이스 목록 조회
```python
res = lf.api.trace.list(
    limit=50,              # 최대 조회 수
    page=1,                # 페이지 번호 (offset 기반)
    name="agent-run",      # 트레이스 이름 필터
    user_id="user-123",    # 사용자 ID 필터
    session_id="sess-abc", # 세션 ID 필터
    tags=["production"],   # 태그 필터 (리스트)
    from_timestamp="2025-01-01T00:00:00Z",  # 시작 시각 (ISO8601)
    to_timestamp="2025-01-31T23:59:59Z",    # 종료 시각 (ISO8601)
    order_by="timestamp.desc",              # 정렬
    version="1.0",         # 버전 필터
    release="prod",        # 릴리스 필터
    environment="production",  # 환경 필터
)
traces = res.data  # list[Trace]
```

#### 트레이스 속성
| 속성 | 타입 | 설명 |
|------|------|------|
| `id` | str | 트레이스 고유 ID |
| `name` | str | 트레이스 이름 |
| `timestamp` | datetime | 시작 시각 |
| `input` | dict/str | 입력 데이터 |
| `output` | dict/str | 출력 데이터 |
| `user_id` | str | 사용자 ID |
| `session_id` | str | 세션 ID |
| `metadata` | dict | 메타데이터 |
| `tags` | list[str] | 태그 목록 |
| `latency` | float | 레이턴시 (초) |
| `total_cost` | float | 총 비용 (USD) |
| `input_tokens` | int | 입력 토큰 수 |
| `output_tokens` | int | 출력 토큰 수 |
| `level` | str | DEBUG/DEFAULT/WARNING/ERROR |
| `version` | str | 버전 |
| `release` | str | 릴리스 |
| `observations` | list | Observation 목록 (get에서만) |
| `scores` | list | Score 목록 (get에서만) |

#### 단일 트레이스 조회
```python
trace = lf.api.trace.get("trace-id-here")
# trace.observations → 모든 observation 포함
# trace.scores → 모든 score 포함
```

#### 페이지네이션
```python
all_traces = []
page = 1
while True:
    res = lf.api.trace.list(limit=100, page=page)
    all_traces.extend(res.data)
    if len(res.data) < 100:
        break
    page += 1
```

### 2. Observation API

```python
# 목록 조회 (v2 권장)
obs = lf.api.observations_v_2.get_many(
    trace_id="trace-id",
    type="GENERATION",     # GENERATION, SPAN, EVENT
    name="llm-call",
    limit=100,
    fields="core,basic,usage",  # 선택적 필드 반환
    from_start_time="2025-01-01T00:00:00Z",
    to_start_time="2025-01-31T23:59:59Z",
)

# 단일 조회
obs = lf.api.observations.get("observation-id")
```

### 3. 세션 API
```python
sessions = lf.api.sessions.list(limit=50)
session = lf.api.sessions.get("session-id")
# session.traces → 세션 내 모든 트레이스
```

### 4. 스코어 API
```python
# 스코어 생성
lf.create_score(
    trace_id="trace-id",
    observation_id="obs-id",  # 선택
    name="quality",
    value=0.85,               # Numeric: float, Boolean: 0/1
    comment="Good quality response",
    data_type="NUMERIC",      # NUMERIC, CATEGORICAL, BOOLEAN
)

# 스코어 목록 조회
scores = lf.api.score.list(limit=50, name="quality")

# 스코어 삭제
lf.api.score.delete("score-id")

lf.flush()  # 반드시 flush
```

### 5. 프롬프트 API
```python
# 프롬프트 조회
prompt = lf.get_prompt("prompt-name", label="production", type="text")
text = prompt.prompt          # 원본 텍스트
compiled = prompt.compile(var1="value1")  # 변수 치환

# 프롬프트 생성/업데이트 (새 버전 자동 생성)
lf.create_prompt(
    name="prompt-name",
    type="text",              # text 또는 chat
    prompt="You are {{role}}. Do {{task}}.",
    labels=["staging"],       # production, staging, 커스텀
)
```

### 6. Metrics API (집계 분석)
```python
import json

query = json.dumps({
    "view": "traces",  # traces, observations, scores-numeric, scores-categorical
    "dimensions": [{"field": "name"}],
    "metrics": [
        {"measure": "count", "aggregation": "count"},
        {"measure": "totalCost", "aggregation": "sum"},
        {"measure": "latency", "aggregation": "p50"},
        {"measure": "totalTokens", "aggregation": "sum"},
    ],
    "timeDimension": {"granularity": "day"},  # hour, day, week, month
    "fromTimestamp": "2025-01-01T00:00:00Z",
    "toTimestamp": "2025-01-31T23:59:59Z",
    "filters": [
        {"column": "name", "operator": "equals", "value": "agent-run", "type": "string"},
        {"column": "userId", "operator": "equals", "value": "user-123", "type": "string"},
    ],
    "orderBy": [{"field": "count", "direction": "desc"}],
    "rowLimit": 100,
})
result = lf.api.metrics.metrics(query=query)
```

#### Metrics — 사용 가능한 지표
| view | measure | 설명 |
|------|---------|------|
| traces | `count` | 트레이스 수 |
| traces | `observationsCount` | observation 수 |
| traces | `latency` | 레이턴시 (초) |
| traces | `totalTokens` | 총 토큰 |
| traces | `totalCost` | 총 비용 (USD) |
| observations | `count` | observation 수 |
| observations | `latency` | 레이턴시 |
| observations | `totalCost` | 비용 |
| observations | `timeToFirstToken` | TTFT |

#### Metrics — aggregation 타입
`sum`, `avg`, `count`, `min`, `max`, `p50`, `p75`, `p90`, `p95`, `p99`

#### Metrics — timeDimension
`hour`, `day`, `week`, `month`, `auto`

### 7. 데이터셋 API
```python
# 데이터셋 목록
datasets = lf.api.datasets.list(limit=20)

# 데이터셋 생성
lf.api.datasets.create(name="eval-set", description="평가용 데이터셋")

# 아이템 추가
lf.api.dataset_items.create(
    dataset_name="eval-set",
    input={"query": "What is AI?"},
    expected_output="AI is...",
    source_trace_id="trace-id",  # 선택: 트레이스에서 가져오기
)

# 아이템 목록
items = lf.api.dataset_items.list(dataset_name="eval-set", limit=50)
```

### 8. 코멘트/주석 API
```python
# 코멘트 생성 (트레이스/observation에 주석 달기)
lf.api.comments.create(
    object_type="TRACE",       # TRACE 또는 OBSERVATION
    object_id="trace-id",
    content="이 응답은 할루시네이션 포함",
    author_user_id="reviewer-1",
)

# 코멘트 조회
comments = lf.api.comments.list(object_type="TRACE", object_id="trace-id")
```

### 9. 모델 관리 API
```python
# 커스텀 모델 등록 (비용 추적용)
lf.api.models.create(
    model_name="my-fine-tuned-gpt4",
    match_pattern="ft:gpt-4.*",
    input_price=0.03,       # per 1K tokens
    output_price=0.06,
    unit="TOKENS",
    tokenizer_id="openai",
)

# 모델 목록
models = lf.api.models.list()
```

### 10. 비동기 API
모든 엔드포인트는 `async_api`로 비동기 호출 가능:
```python
trace = await lf.async_api.trace.get("trace-id")
traces = await lf.async_api.trace.list(limit=100)
```

---

## 워크플로 가이드

### Observe → Analyze → Act → Report

1. **Observe**: 데이터 수집
   - `list_traces`로 필터링 조회 (이름, 사용자, 세션, 날짜)
   - `list_sessions`로 세션 단위 조회
   - `query_metrics`로 집계 데이터 수집

2. **Analyze**: 분석 및 인사이트
   - `think_tool`로 전략 수립
   - `get_trace_detail`로 개별 트레이스 심층 분석
   - 성능 병목, 에러 패턴, 비용 이상 식별

3. **Act**: 조치 실행
   - `evaluate_with_llm`으로 자동 품질 평가
   - `suggest_prompt_improvement`로 프롬프트 개선
   - `save_langfuse_prompt`로 개선 프롬프트 저장
   - `create_score`로 수동 평가 기록

4. **Report**: 보고서 생성
   - `generate_report`로 일간/주간/월간 보고서 생성
   - `write_file`로 마크다운 보고서 저장
   - `manage_datasets`로 평가 데이터셋 관리

### 보고서 생성 가이드

#### 일간 보고서 구조
```markdown
# LLMOps 일간 보고서 — {날짜}

## 핵심 지표
| 지표 | 값 | 전일 대비 |
|------|---|---------|
| 트레이스 수 | 1,234 | +5.2% |
| 평균 레이턴시 | 2.3s | -0.1s |
| 총 비용 | $12.45 | +$1.20 |
| 에러율 | 0.8% | -0.2% |

## 주요 발견
1. ...
2. ...

## 권장 조치
1. ...
```

#### 주간/월간 보고서에 추가할 섹션
- 프롬프트 버전별 성능 비교
- 사용자별 사용량 분석
- 모델별 비용 분석
- 품질 트렌드 (LLM-as-judge 점수 추이)
- 이상 탐지 결과

### LLM-as-judge 평가 가이드

#### 평가 기준 (기본)
| 기준 | 점수 | 설명 |
|------|------|------|
| 정확성 | 1-5 | 사실 기반 응답 여부 |
| 완전성 | 1-5 | 질문에 대한 충분한 답변 |
| 유용성 | 1-5 | 실질적 도움이 되는 정보 |
| 안전성 | 1-5 | 유해/편향 콘텐츠 부재 |
| 일관성 | 1-5 | 문맥과의 논리적 일관성 |

#### 종합점수 계산
`종합점수 = (정확성 + 완전성 + 유용성 + 안전성 + 일관성) / 25`

### 프롬프트 개선 가이드
1. 현재 프롬프트 조회 → `get_langfuse_prompt`
2. 관련 트레이스에서 저품질 응답 수집 → `list_traces` + `list_scores`
3. 문제 패턴 분석 → `think_tool`
4. 개선안 생성 → `suggest_prompt_improvement`
5. staging 라벨로 저장 → `save_langfuse_prompt`
6. A/B 비교 후 production 승격

### 데이터셋 관리 가이드
- 평가 데이터셋: 대표적 입출력 쌍 수집
- 골든 데이터셋: 기대 출력이 있는 벤치마크
- 회귀 테스트: 프롬프트 변경 시 기존 품질 유지 확인
