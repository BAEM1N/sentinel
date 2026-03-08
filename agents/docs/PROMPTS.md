# Sentinel Prompts Reference

## 1. System Prompt (`prompts.py`)

에이전트의 전체 행동을 정의하는 시스템 프롬프트.

### 핵심 역할 (5개)
1. **트레이스 분석가** — 패턴 분석, 병목 감지, 에러 진단, 이상 탐지
2. **프롬프트 엔지니어** — 버전 관리, A/B 비교, 데이터 기반 개선
3. **품질 평가사** — LLM-as-judge, 리그레션 감지, 스코어 관리
4. **리포터** — 일간/주간/월간 보고서, 비용 최적화
5. **플랫폼 관리자** — 데이터셋, 주석, 모델 관리

### 워크플로: Observe → Analyze → Act → Report
1. `list_traces` / `list_sessions` / `query_metrics` 로 데이터 수집
2. `think_tool` 로 분석, 인사이트 도출
3. 프롬프트 개선, 평가 실행, 스코어 기록
4. `generate_report` → `write_file` 저장

### 규칙
- 분석 전 `think_tool`로 전략 수립
- 수치 데이터는 표 형식
- before/after 명확히
- 비용 데이터 항상 포함
- 복잡한 분석은 서브에이전트 위임

## 2. Report MD Prompt (`metrics.py` → `REPORT_MD_PROMPT`)

LLM에게 McKinsey 스타일 Markdown 보고서를 생성하도록 지시.

### 삽입 변수
| 변수 | 설명 |
|------|------|
| `{period_kr}` | 일간/주간/월간 |
| `{from_ts}`, `{to_ts}` | 조회 기간 |
| `{date_label}` | `YYYY-MM-DD ~ YYYY-MM-DD` |
| `{generated_at}` | 생성 시각 |
| `{metrics_json}` | Metrics API 집계 JSON |
| `{traces_json}` | 트레이스 샘플 JSON (30건) |
| `{scores_json}` | 스코어 JSON |

### 출력 구조
```
# LLMOps {기간} 보고서
Executive Summary (3문장)
1. 핵심 지표 (6항목 표)
2. 트레이스 분석 (이름별/사용자별/시간대별)
3. 비용 분석 (분포/고비용 TOP 3/최적화)
4. 품질 분석 (스코어/에러)
5. 권장 조치 ([긴급]/[중요]/[개선])
부록
```

### 핵심 규칙
- "Markdown만 출력 (코드 블록 없이)"
- "데이터에 없는 수치를 지어내지 마세요"
- "톤은 간결하고 전문적, 불필요한 수식어 배제"

## 3. Report HTML Prompt (`metrics.py` → `REPORT_HTML_PROMPT`)

HTML body 생성용. 구조는 MD와 동일하나 HTML 태그 + CSS 클래스 사용.

### 사용하는 CSS 클래스
| 클래스 | 용도 |
|--------|------|
| `report-header` | 헤더 영역 (제목, 부제, 메타) |
| `summary-box` | Executive Summary 박스 |
| `section-title` | 섹션 제목 (`h2`) |
| `kpi-grid`, `kpi-card` | KPI 그리드 (3열) |
| `kpi-card.highlight` | 강조 카드 |
| `kpi-card.warning` | 경고 (노란색) |
| `kpi-card.danger` | 위험 (빨간색) |
| `num`, `cost`, `high-cost`, `latency` | 테이블 셀 스타일 |
| `alert-critical`, `alert-warning`, `alert-info` | 알림 등급 |
| `badge-critical`, `badge-important`, `badge-improve` | 배지 |
| `action-list` | 권장 조치 리스트 |

## 4. LLM-as-judge Prompt (`evaluation.py`)

### 입력
- 트레이스의 input (2000자) + output (2000자)
- 평가 기준 (기본: 정확성, 완전성, 유용성, 안전성, 일관성)

### 출력 형식
```
### 기준별 평가
- **점수**: N/5
- **근거**: ...
- **개선 피드백**: ...

### 종합 진단
### 프롬프트 개선 제안
### 점수 요약 (표)

종합점수: X.XX
```

### 점수 추출
- 정규식: `종합점수[:\s]*([\d.]+)`
- 범위: 0.00 ~ 1.00 (clamp)
- 프롬프트 개선 제안을 comment에 포함 (300자)

## 5. Prompt Improvement (`prompt_mgmt.py`)

### 입력
- 현재 프롬프트 텍스트
- 관찰된 문제점

### 출력
1. 문제 원인 분석
2. 개선된 프롬프트 (전문)
3. 변경 사항 요약
4. 예상 개선 효과

## 6. Subagent Prompts (`subagents.py`)

### trace-analyst
- "트레이스/세션 데이터 분석 전문가"
- 필터 적극 활용, query_metrics → 개별 드릴다운
- 결과에 '핵심 발견', '권장 조치' 포함

### prompt-optimizer
- "프롬프트 엔지니어링 전문가"
- get_langfuse_prompt → list_traces → suggest_improvement → staging 저장
- A/B 비교 시 버전별 성능 지표 표 정리

### quality-evaluator
- "LLM 품질 평가 전문가"
- list_traces → evaluate_with_llm → 품질 트렌드 → generate_report
- 평가 기준: 정확성, 완전성, 유용성, 안전성, 일관성
