# Sentinel 개발 방향성

- 영역: Product / Agent / Web / Platform
- 분류: 방향성 문서
- 우선순위: 최상위
- 상태: 초안
- 기준일: 2026-03-08

## 1. 이 문서가 다루는 범위

이 문서는 Sentinel을 **Langfuse 기반 LLMOps 도구**에서 한 단계 확장하여, **프로덕션 AI 시스템을 운영하는 AI Operator / Control Plane**으로 발전시키기 위한 중장기 개발 방향을 정리합니다.

이 문서가 다루는 내용은 다음과 같습니다.

- Sentinel의 제품 테제(Product Thesis)
- LangSmith Polly, Braintrust Loop, Arize Alyx/Phoenix, Helicone MCP에서 가져와야 할 강점
- Sentinel이 과투자(over-invest)해야 할 차별화 영역
- 단계별 제품/기술 로드맵
- 현재 코드베이스 기준의 아키텍처 함의
- 성공 지표와 리스크

이 문서는 단일 기능 제안서가 아니라, 향후 개별 기능 문서(AG-xx, WEB-xx, WF-xx)를 이끄는 **상위 방향성 문서**입니다.

---

## 2. 요약

Sentinel은 단순한 LLMOps 분석 도우미가 아니라, 다음을 수행하는 시스템으로 진화해야 합니다.

1. **관측(Observe)**  
   traces, sessions, metrics, prompts, scores, datasets, annotations를 읽는다.
2. **이해(Understand)**  
   실패 패턴, 품질 저하, 비용 이상, 프롬프트 문제를 문맥적으로 해석한다.
3. **결정(Decide)**  
   무엇을 고치고, 무엇을 승인 요청하고, 무엇을 배포/발행해야 하는지 제안한다.
4. **실행(Operate)**  
   보고서 생성, 알림 전송, 플레이북 실행, 배치 평가, 승인 후 발행을 수행한다.
5. **거버넌스(Govern)**  
   모든 중요한 액션에 대해 승인, 감사 로그, 변경 이력, 운영 책임성을 남긴다.

핵심 방향은 다음 한 줄로 정리할 수 있습니다.

> **Sentinel = Observability Copilot가 아니라, Governable AI Operations Operator**

경쟁 제품들이 잘하는 **분석 UX**, **폐쇄루프 품질 개선**, **실험/디버깅**, **MCP 채널**은 과감하게 가져오되, Sentinel은 그 위에 **운영 자동화**, **승인/감사**, **정기 운영 리듬**, **행동 가능한 워크플로**를 더 강하게 쌓아야 합니다.

---

## 3. 현재 Sentinel의 위치

### 3.1 현재 코드 기준 강점

현재 저장소에는 이미 운영형 LLMOps 시스템의 씨앗이 존재합니다.

- Agent / tool 기반 LLMOps 인터페이스
  - `sentinel/agent.py`
  - `sentinel/tools/`
- Web 기반 운영 대시보드
  - `sentinel/web/app.py`
  - `sentinel/web/routes.py`
- 보고서 생성 및 스케줄 운영
  - `sentinel/services/report_service.py`
  - `sentinel/web/scheduler.py`
  - `sentinel/web/notify.py`
- 승인/감사/알림/플레이북
  - `sentinel/approval.py`
  - `sentinel/audit.py`
  - `sentinel/alerts.py`
  - `sentinel/playbook.py`
- 백그라운드 작업 처리
  - `sentinel/services/job_manager.py`

즉 Sentinel은 이미 단순 dashboard가 아니라, **운영 시스템으로 확장 가능한 기반**을 갖고 있습니다.

### 3.2 현재 코드 기준 약점

반면 현재 구조는 아직 다음 한계를 가집니다.

- 제품의 정체성이 “분석 도구”와 “운영 시스템” 사이에서 명확히 정리되지 않음
- `sentinel/web/routes.py`에 기능이 과집중되어 기능 확장 속도를 구조가 따라가지 못함
- semantic search, failure clustering, experiment compare, MCP surface가 없음
- prompt / eval / dataset / reports / approvals를 하나의 사용자 여정으로 묶는 상위 UX가 약함
- 운영 거버넌스의 씨앗은 있으나, 제품 메시지와 구조가 아직 그 가치를 전면화하지 못함

---

## 4. 제품 테제 (Product Thesis)

### 4.1 핵심 테제

Sentinel은 다음 질문에 답해야 합니다.

> “프로덕션 LLM 시스템을 운영하는 팀이, 문제를 찾고 설명받는 수준을 넘어 실제 운영 행위를 안전하게 수행하려면 어떤 소프트웨어가 필요한가?”

Sentinel의 답은 다음과 같습니다.

> **Sentinel은 LLMOps 데이터 위에서 동작하는 AI Operator이며, 팀이 프로덕션 AI 시스템을 분석·승인·실행·감사 가능한 방식으로 운영하게 해주는 Control Plane이다.**

### 4.2 왜 이 테제가 중요한가

대부분의 observability assistant는 다음까지만 강합니다.

- 문제를 설명한다
- 트레이스를 요약한다
- 프롬프트 개선안을 제안한다
- 실험 후보를 추천한다

하지만 실제 운영팀이 반복적으로 수행하는 일은 그 다음 단계입니다.

- 이 보고서를 발행할 것인가?
- 이 프롬프트 변경을 staging에서 production으로 승격할 것인가?
- 이 알림 규칙을 활성화할 것인가?
- 이 실패 패턴을 바탕으로 어떤 평가 루프를 돌릴 것인가?
- 누구의 승인 아래 자동화가 실행되었는가?
- 지난주 운영 개선이 실제 비용/품질에 어떤 변화를 만들었는가?

Sentinel은 바로 이 지점을 메워야 합니다.

### 4.3 제품 카테고리 정의

Sentinel이 속해야 하는 카테고리는 다음과 같습니다.

- AI Observability Tool: 아님
- AI Copilot for LLMOps: 부분적으로만 해당
- LLMOps Dashboard: 일부 해당
- **AI Operations Control Plane: 지향해야 하는 최종 카테고리**

### 4.4 Sentinel의 핵심 메시지

제품 메시지는 다음 방향이 적합합니다.

- **From observability to governable action**
- **Sentinel turns LLMOps insight into audited operations**
- **The operator for production AI systems**
- **Analyze, approve, execute, audit**

---

## 5. 경쟁군 기준 벤치마크 방향

이 문서는 다음 4개 제품군을 기준으로 벤치마크합니다.

1. LangSmith Polly
2. Braintrust Loop
3. Arize Alyx / Phoenix
4. Helicone MCP

이들을 단순 복제 대상이 아니라, **흡수해야 할 장점과 차별화해야 할 빈틈을 제공하는 기준점**으로 봅니다.

### 5.1 LangSmith Polly에서 배워야 할 것

#### Polly의 핵심 강점

- trace / thread / prompt / dataset / annotation 문맥에 직접 붙는 보조 에이전트 UX
- “현재 페이지의 객체를 이해한 상태”에서 대화하는 능력
- 분석과 prompt engineering을 자연어 인터페이스로 직접 연결하는 경험

#### Sentinel이 가져와야 할 것

- 페이지별 내장형 코파일럿
- 객체 문맥 자동 주입
- 보고 있는 화면에서 바로 다음 액션을 추천하는 UX
- prompt / trace / report / eval 각 화면에서의 작업 특화 assistant

#### Sentinel 적용 예시

- Trace Detail 우측 패널:
  - 실패 원인 요약
  - 유사 실패 trace 추천
  - dataset 항목 후보 생성
  - 평가/리뷰/알림으로 연결
- Prompt Detail 우측 패널:
  - 문제 패턴 요약
  - 개선 초안
  - staging 저장 / approval 요청
- Report View 우측 패널:
  - 발행 전 점검
  - 승인 상태 요약
  - 후속 조치 playbook 추천

#### 요약

Polly가 주는 가장 큰 교훈은 **“assistant는 별도 화면이 아니라 객체 문맥 속에 있어야 한다”**는 점입니다.

### 5.2 Braintrust Loop에서 배워야 할 것

#### Loop의 핵심 강점

- production logs에서 바로 개선 루프를 시작하는 경험
- semantic search, filter generation, similar traces
- dataset, scorer, chart, experiment를 자연어로 연결하는 폐쇄루프
- 팀 단위로 품질 개선 워크플로를 돌릴 수 있는 제품화 수준

#### Sentinel이 가져와야 할 것

- trace → cluster → dataset → eval → prompt 개선 → 재검증 루프
- 자연어 기반 분석을 데이터 구조화 작업으로 연결하는 능력
- 운영자의 “무엇을 해야 할지 모르겠다” 상태를 “바로 실행 가능한 개선 흐름”으로 전환하는 UX

#### Sentinel 적용 예시

- “최근 7일 실패 trace 중 유사 원인별로 묶어줘”
- “이 그룹에서 eval dataset 후보 20개 만들어줘”
- “이 패턴을 잡는 judge rubric 초안 만들어줘”
- “이 prompt의 staging 후보와 기존 production 성능 비교 리포트 생성해줘”

#### 요약

Loop가 주는 가장 큰 교훈은 **“LLMOps assistant는 분석으로 끝나면 안 되고, 개선 루프를 닫아야 한다”**는 점입니다.

### 5.3 Arize Alyx / Phoenix에서 배워야 할 것

#### Alyx / Phoenix의 핵심 강점

- trace troubleshooting
- explicit context 기반 에이전트 동작
- agent trajectory / session 수준 분석
- prompt learning, experiments, datasets
- MCP server 및 agent integration

#### Sentinel이 가져와야 할 것

- agent trajectory 뷰
- session-level failure diagnosis
- prompt learning / recommendation layer
- assistant가 span / score / metadata를 구조적으로 이해하는 능력
- 외부 coding agent와 연결되는 MCP surface

#### Sentinel 적용 예시

- Trace Detail에 “trajectory mode” 추가
- Session Detail에서 “이 세션이 실패한 핵심 turning point 3개” 요약
- Prompt registry에 “최근 실패 trace 기준 자동 개선 후보” 제시
- Claude/Codex/Cursor에서 Sentinel을 바로 호출할 수 있는 MCP server 제공

#### 요약

Alyx / Phoenix가 주는 가장 큰 교훈은 **“에이전트를 운영하려면 단일 trace보다 trajectory와 context graph를 봐야 한다”**는 점입니다.

### 5.4 Helicone MCP에서 배워야 할 것

#### Helicone MCP의 핵심 강점

- 아주 가벼운 MCP surface
- 기존 coding assistant와 즉시 연결되는 채널 전략
- 제품 내부 assistant가 없어도 사용자가 익숙한 인터페이스에서 observability 작업 수행 가능

#### Sentinel이 가져와야 할 것

- Sentinel MCP server
- low-friction read/query toolset
- Web UI 밖에서도 동작하는 운영 채널

#### Sentinel 적용 예시

- `search_traces`
- `get_trace_detail`
- `get_prompt`
- `compare_prompt_versions`
- `generate_report`
- `request_approval`
- `query_audit_log`
- `run_playbook`

#### 요약

Helicone이 주는 가장 큰 교훈은 **“assistant는 제품 안에만 있으면 안 되고, 사용자가 이미 일하는 도구로 들어가야 한다”**는 점입니다.

---

## 6. Sentinel이 과투자해야 할 차별화 영역

Sentinel은 경쟁 제품의 장점을 흡수하되, 모두가 잘하지 못하는 영역에 더 강하게 투자해야 합니다.

### 6.1 운영 자동화 (Operations Automation)

이 영역은 Sentinel의 가장 강한 차별화 포인트가 될 수 있습니다.

#### 집중해야 할 기능

- 일정 기반 정기 운영 리포트
- quality / cost / release regression 운영 점검 playbook
- background jobs
- notifications
- publish workflows
- review inbox

#### 왜 중요한가

실제 운영팀은 매일 다음을 반복합니다.

- 상태를 확인한다
- 이상 징후를 정리한다
- 보고한다
- 승인받는다
- 액션을 수행한다
- 기록을 남긴다

경쟁 제품들이 “분석”에 더 강하다면, Sentinel은 “운영 반복”에 훨씬 더 강해야 합니다.

### 6.2 거버넌스와 책임성 (Governance & Accountability)

이 영역은 Sentinel이 강하게 브랜딩해야 할 축입니다.

#### 집중해야 할 기능

- approval gates
- audit trails
- role-based actions
- policy-aware automation
- publish/change control
- who/why/when 기록

#### 핵심 메시지

Sentinel은 “무엇을 추천했는가”보다 다음을 더 중요하게 다뤄야 합니다.

- 누가 승인했는가
- 무엇이 실행되었는가
- 어떤 근거로 실행되었는가
- 어떤 변경이 production에 반영되었는가

### 6.3 개선 루프의 운영화 (Operationalized Improvement Loop)

Loop와 Phoenix에서 배운 개선 루프를 Sentinel 방식으로 재정의해야 합니다.

#### 지향 상태

Observe → Cluster → Dataset → Evaluate → Propose Change → Approve → Deploy/Publish → Monitor → Report

#### Sentinel식 차별화

- 개선 루프 자체가 governance-aware 해야 함
- 자동화는 approval-aware 해야 함
- 결과는 report / audit / notification으로 이어져야 함

### 6.4 다중 인터페이스 제어면 (Multi-Surface Control Plane)

Sentinel은 단일 웹앱이 아니라 여러 표면을 가져야 합니다.

#### 필요한 표면

- Web UI
- CLI
- MCP
- 향후 Slack / ChatOps surface

#### 이유

운영자는 항상 브라우저에서만 일하지 않습니다. IDE, 터미널, 채팅 도구에서도 동일한 운영 컨텍스트를 이어가야 합니다.

### 6.5 조직 기억과 반복성 (Operational Memory)

Sentinel은 단회성 질문 응답형 assistant가 아니라, **조직의 운영 기억을 축적하는 시스템**이 되어야 합니다.

#### 집중해야 할 기능

- run history
- playbook history
- incident postmortem links
- recurring pattern memory
- saved queries / saved investigations
- “지난번에는 어떻게 대응했는가” 재사용

---

## 7. 제품 차별화 문장

### 7.1 경쟁 제품과의 차이

#### Polly와의 차이

- Polly는 AI agent engineer에 가깝다.
- Sentinel은 AI operations operator에 가깝다.

#### Loop와의 차이

- Loop는 quality optimization loop에 강하다.
- Sentinel은 operational governance loop에 강해야 한다.

#### Alyx / Phoenix와의 차이

- Alyx / Phoenix는 debugging + experimentation ecosystem에 강하다.
- Sentinel은 production-safe action orchestration에 강해야 한다.

#### Helicone MCP와의 차이

- Helicone은 access surface에 강하다.
- Sentinel은 action + policy + audit에 강해야 한다.

### 7.2 가장 중요한 차별화 문장

다음 문장들이 Sentinel의 핵심 차별화 메시지 후보입니다.

- **Sentinel is the operator for production AI systems.**
- **Sentinel closes the loop from insight to governed action.**
- **Not just observability. Operability.**
- **Analyze, approve, execute, audit.**

---

## 8. 핵심 사용자와 주요 Jobs To Be Done

### 8.1 Primary Persona

#### LLMOps 운영자 / AI 플랫폼 오너

이 사용자는 다음을 책임집니다.

- 비용과 성능의 안정화
- release 품질 검증
- prompt / model 변경의 운영 통제
- 운영 리포트 작성과 공유
- 이상 징후 탐지
- 반복 운영 워크플로의 자동화

### 8.2 Secondary Persona

#### AI 애플리케이션 개발자 / Prompt Engineer

이 사용자는 다음을 원합니다.

- trace 기반 디버깅
- prompt 개선 초안
- batch eval 실행
- dataset 작성 자동화
- deployment 전 품질 확인

### 8.3 Tertiary Persona

#### 팀 리드 / 매니저 / 이해관계자

이 사용자는 다음을 원합니다.

- 지난주 AI 운영 상태 요약
- 승인된 변경 이력
- 품질/비용 트렌드
- 위험도 높은 이슈의 우선순위

### 8.4 핵심 JTBD

- “최근 릴리즈 이후 품질이 나빠졌는지 빠르게 알고 싶다.”
- “반복되는 실패 패턴을 평가셋으로 만들고 싶다.”
- “프롬프트 변경을 production에 올리기 전에 안전하게 승인하고 싶다.”
- “운영 리포트를 매주 자동 생성하고 싶다.”
- “나중에 누가 어떤 자동화를 실행했는지 감사할 수 있어야 한다.”
- “웹이든 IDE든 어디서든 Sentinel을 호출하고 싶다.”

---

## 9. 목표 제품 구조

Sentinel의 목표 제품 구조는 다음 4층으로 정리할 수 있습니다.

### 9.1 Layer 1 — Observability Ingestion

- traces
- sessions
- scores
- prompts
- datasets
- annotations
- metrics

현재 Sentinel은 이 계층을 Langfuse API 기반으로 상당 부분 갖고 있습니다.

### 9.2 Layer 2 — Intelligence Layer

이 계층은 아직 보강이 많이 필요합니다.

#### 필요한 기능

- semantic retrieval
- trace clustering
- regression detection
- trajectory analysis
- prompt learning
- recommendation engine

### 9.3 Layer 3 — Action Layer

이 계층이 Sentinel의 본체가 되어야 합니다.

#### 필요한 기능

- report generation
- alerting
- dataset creation
- evaluation orchestration
- prompt promotion workflow
- playbook execution
- publish actions

### 9.4 Layer 4 — Governance Layer

이 계층이 Sentinel의 차별화 코어입니다.

#### 필요한 기능

- approvals
- audit logs
- policy checks
- role-based access
- action history
- operator accountability

---

## 10. 단계별 개발 로드맵

### Phase 0 — Foundation Hardening

이 단계는 기능 확장 전에 반드시 수행해야 하는 기반 정리 단계입니다.

#### 목표

- 확장 가능한 구조 확보
- 운영 안정성 개선
- 제품 방향을 담을 수 있는 기본 골격 확보

#### 핵심 작업

- `sentinel/web/routes.py` 기능별 분리
- `config.py` 전역 초기화 축소
- Job / approval / audit / alerts / playbook 공통 persistence 패턴 정리
- runtime 디렉토리 구조 정리
- tests 기초 세팅
- auth / session / secure cookie / 운영 기본값 하드닝

#### 완료 기준

- 제품 방향 문서에서 제안하는 Phase 1 기능을 구조적 무리 없이 넣을 수 있어야 함

### Phase 1 — Embedded Copilot

이 단계의 목적은 Sentinel을 “기능 모음”에서 “문맥형 assistant 제품”으로 전환하는 것입니다.

#### 목표

- 각 운영 객체 화면에서 assistant를 자연스럽게 사용할 수 있어야 함

#### 핵심 기능

- Trace Copilot
- Prompt Copilot
- Report Copilot
- Eval Copilot
- Action suggestions

#### 세부 항목

- 페이지 컨텍스트 자동 수집
- 객체별 system prompt 분리
- 추천 액션 카드
- conversation state 저장
- 결과를 바로 dataset / approval / report / playbook으로 연결

#### 성공 기준

- 사용자가 별도 CLI 없이 웹 화면에서 자연어로 주요 작업을 수행할 수 있음

### Phase 2 — Closed Improvement Loop

이 단계의 목적은 관측 데이터를 실제 개선 루프로 연결하는 것입니다.

#### 목표

- trace 기반 품질 개선 루프를 Sentinel 안에서 닫는다

#### 핵심 기능

- similar failure clustering
- dataset builder from trace groups
- batch eval campaigns
- prompt candidate generation
- staging vs production compare

#### 세부 항목

- semantic indexing
- clustering jobs
- eval plan templates
- prompt diff & promotion
- 결과 비교 report

#### 성공 기준

- 사용자가 문제 발견 후 별도 외부 도구 없이 개선 루프를 1개 화면 흐름에서 완료 가능

### Phase 3 — Multi-Surface Control Plane

이 단계의 목적은 Sentinel을 web-local 도구가 아니라 운영 인터페이스 플랫폼으로 만드는 것입니다.

#### 목표

- Web / CLI / MCP 간 일관된 action model 확보

#### 핵심 기능

- Sentinel MCP server
- 공통 action schema
- external agent integration
- saved workflows across surfaces

#### 세부 항목

- MCP tools 설계
- auth / policy integration
- approval-aware remote action
- audit trail integration

#### 성공 기준

- Claude/Codex/Cursor에서도 Sentinel 운영 기능을 안전하게 호출 가능

### Phase 4 — Governed Automation

이 단계의 목적은 Sentinel을 AI 운영 자동화 시스템으로 끌어올리는 것입니다.

#### 목표

- 규칙 기반 + 승인 기반 자동 운영

#### 핵심 기능

- policy-driven automation
- scheduled playbooks
- release guardrails
- approval chains
- incident / review workflows

#### 세부 항목

- 위험도 기반 승인 레벨
- 변경 유형별 policy
- report publish gates
- review inbox triage
- postmortem linkage

#### 성공 기준

- 운영팀이 반복 작업의 상당 부분을 Sentinel에 위임하되, 통제력과 감사 가능성을 유지

---

## 11. 아키텍처 함의

이 방향성을 구현하려면, 단순 기능 추가가 아니라 아키텍처 재구성이 필요합니다.

### 11.1 Web Layer 재구성

현재 `sentinel/web/routes.py` 단일 파일 구조는 제품 확장에 불리합니다.

#### 목표 구조

```text
sentinel/web/
├── app.py
├── routes/
│   ├── auth.py
│   ├── reports.py
│   ├── traces.py
│   ├── prompts.py
│   ├── evals.py
│   ├── datasets.py
│   ├── approvals.py
│   ├── audit.py
│   ├── alerts.py
│   ├── playbooks.py
│   └── settings.py
├── views/
├── api/
└── copilot/
```

#### 이유

- 화면별 assistant 주입이 쉬워짐
- 기능 소유권이 명확해짐
- 테스트가 쉬워짐

### 11.2 Service Layer 강화

현재 보고서 생성 서비스는 좋은 출발점이지만, 제품 방향을 담기엔 부족합니다.

#### 필요한 서비스 계층

- `trace_intelligence_service`
- `prompt_optimization_service`
- `evaluation_service`
- `dataset_service`
- `action_service`
- `governance_service`
- `playbook_service`
- `reporting_service`

#### 역할

- route는 요청/응답만 담당
- service가 제품 로직 담당
- tool은 agent 호출 surface만 담당

### 11.3 Intelligence Layer 신설

경쟁 제품의 강점을 흡수하려면 intelligence 전용 계층이 필요합니다.

#### 필요한 모듈

- clustering
- similarity retrieval
- session summarization
- failure taxonomy
- recommendation engine

#### 기술적 고려

- embeddings / vector index
- background indexing jobs
- trace normalization
- cached summaries

### 11.4 Action Schema 통일

Web, CLI, MCP, Playbook에서 동일한 액션을 호출할 수 있어야 합니다.

#### 필요한 개념

- `ActionRequest`
- `ActionResult`
- `ApprovalRequirement`
- `AuditEnvelope`
- `ExecutionContext`

#### 이유

- 인터페이스가 달라도 동일한 운영 행위를 공유할 수 있어야 함
- MCP 추가 시 재사용 가능

### 11.5 Governance Kernel

Sentinel의 차별화 핵심이므로 별도 커널처럼 다뤄야 합니다.

#### 포함 요소

- approval policies
- audit logging
- actor identity
- action classification
- mutation vs read-only distinction
- risk scoring

### 11.6 Background Execution 강화

현 JobManager는 출발점으로 충분하지만, 중장기적으로는 더 강해져야 합니다.

#### 필요 기능

- persisted jobs
- retries
- timeouts
- cancellation
- progress tracking
- resumability

#### 이유

- dataset building, eval campaign, clustering, playbook run은 장시간 작업이 될 가능성이 큼

### 11.7 MCP Surface

MCP는 단일 부가기능이 아니라 제품 채널입니다.

#### 필수 툴 후보

- `search_traces`
- `get_trace_detail`
- `search_similar_failures`
- `list_prompts`
- `get_prompt_detail`
- `generate_prompt_candidate`
- `create_dataset_from_trace_group`
- `run_batch_eval`
- `generate_report`
- `request_approval`
- `publish_report`
- `query_audit`
- `run_playbook`

#### 설계 원칙

- read-only tool과 mutation tool 분리
- mutation tool은 approval-aware
- audit metadata 자동 첨부

---

## 12. 정보 구조와 사용자 경험 방향

### 12.1 핵심 객체 중심 UX

Sentinel의 UX는 “기능 메뉴” 중심이 아니라 “운영 객체” 중심이어야 합니다.

#### 운영 객체

- Trace
- Session
- Prompt
- Evaluation Run
- Dataset
- Report
- Approval
- Alert
- Playbook
- Incident / Review Item

각 객체는 다음 공통 패턴을 가져야 합니다.

- 상태 요약
- 관련 컨텍스트
- 추천 액션
- 실행 이력
- 승인/감사 정보
- assistant 패널

### 12.2 홈 화면의 역할

대시보드는 단순 KPI 나열이 아니라 **운영 큐의 우선순위 보드**가 되어야 합니다.

#### 반드시 보여야 할 것

- 긴급 경보
- 승인 대기
- 품질 저하 리뷰 큐
- 예정된 리포트/플레이북
- 최근 실행된 자동화
- 지난 7일 주요 인사이트

### 12.3 “다음 액션” UX

Sentinel의 핵심은 분석 결과를 행동으로 연결하는 데 있습니다.

각 화면은 다음 액션을 명시해야 합니다.

- 이 trace에서 dataset 만들기
- 이 prompt 후보를 staging에 저장하기
- 이 리포트를 승인 요청하기
- 이 패턴으로 alert rule 만들기
- 이 케이스를 review inbox로 보내기

---

## 13. 성공 지표

성공 지표는 단순 사용량이 아니라, **운영 행위가 얼마나 구조화되고 자동화되었는가**를 측정해야 합니다.

### 13.1 제품 사용 지표

- Weekly Active Operators
- Web Copilot session 수
- MCP 호출 수
- Playbook 실행 수
- 승인 요청 수 / 승인 완료 수
- 자동 생성 report 수

### 13.2 운영 효율 지표

- issue 발견 → 첫 액션까지의 시간
- prompt 개선 아이디어 → staging 반영까지의 시간
- report 생성 시간
- approval turnaround time
- review inbox 처리 시간

### 13.3 품질 개선 지표

- dataset 생성 후 eval 실행 전환율
- eval 결과 기반 prompt 변경 비율
- quality regression 탐지 lead time
- 반복 실패 패턴 재발 감소율

### 13.4 거버넌스 지표

- audit-covered action 비율
- approval-required action 중 실제 승인 경유 비율
- 승인 없이 실행된 mutation 수
- publish action의 actor traceability 비율

### 13.5 기술 지표

- assistant latency
- background job 성공률
- scheduler reliability
- MCP tool 성공률
- notification delivery 성공률

---

## 14. 리스크와 대응

### 14.1 범위 폭발 (Scope Explosion)

#### 리스크

Polly, Loop, Alyx, Helicone의 장점을 모두 흡수하려다 제품이 산만해질 수 있습니다.

#### 대응

- “운영 자동화 + 거버넌스”를 최상위 축으로 고정
- 모든 기능은 Observe/Understand/Operate/Govern 4축에 매핑
- 그 어디에도 속하지 않으면 우선순위 하향

### 14.2 분석형 도우미로의 회귀

#### 리스크

assistant UX만 강화하다 보면 Sentinel이 또 하나의 “질문 답변형 코파일럿”에 머무를 수 있습니다.

#### 대응

- 모든 주요 assistant 결과는 action path를 제공해야 함
- 요약만 제공하고 끝나는 기능은 후순위로 둠

### 14.3 과도한 자동화

#### 리스크

운영 자동화가 커질수록 잘못된 추천/실행의 위험이 커집니다.

#### 대응

- mutation action 분류
- approval gates
- dry-run
- audit envelope
- 위험도 기반 정책

### 14.4 Langfuse 결합도

#### 리스크

현재 Sentinel은 Langfuse-native이므로 플랫폼 결합도가 높습니다.

#### 대응

- 내부 도메인 모델은 vendor-agnostic하게 설계
- adapter layer 도입
- MCP / service layer는 Langfuse raw response에 덜 의존하도록 정리

### 14.5 아키텍처 부채

#### 리스크

현재 구조 위에 기능을 계속 얹으면 유지보수 비용이 급증할 수 있습니다.

#### 대응

- Phase 0를 강제
- route 분리
- service extraction
- common action schema
- persistence 정리

### 14.6 신뢰성 문제

#### 리스크

assistant가 틀린 판단을 하거나 noisy alert를 만들 수 있습니다.

#### 대응

- recommendation confidence
- human review queue
- feedback capture
- false positive 측정
- explainability metadata 저장

---

## 15. 우선순위 원칙

향후 모든 기능 제안은 아래 원칙으로 우선순위를 정합니다.

### 15.1 원칙 1 — 운영으로 이어지지 않는 기능은 후순위

분석만 하고 행동으로 연결되지 않으면 우선순위를 낮춥니다.

### 15.2 원칙 2 — 거버넌스를 강화하는 기능은 가산점

approval, audit, policy, accountability를 강화하는 기능은 우선합니다.

### 15.3 원칙 3 — 여러 surface에 재사용 가능한 기능을 우선

Web / CLI / MCP 모두에서 재사용 가능한 action/service를 우선합니다.

### 15.4 원칙 4 — 팀 운영 리듬에 직접 기여하는 기능을 우선

정기 리포트, 리뷰 큐, 플레이북, 승인 흐름처럼 조직의 반복 루틴을 정착시키는 기능을 우선합니다.

---

## 16. 향후 문서 분해 방향

이 문서는 상위 방향성 문서이며, 아래 하위 문서로 쪼개져야 합니다.

### Agent / Backend 쪽

- Semantic trace clustering
- Recommendation engine
- Action schema standardization
- MCP server design
- Governance kernel
- Persistent jobs / workflow runtime

### Web / UX 쪽

- Trace Copilot UI
- Prompt Copilot UI
- Report Copilot UI
- Ops dashboard redesign
- Review / Approval / Incident workspace
- Multi-surface UX contract

### Product / Strategy 쪽

- Persona & JTBD
- KPI framework
- Rollout strategy
- Pricing / packaging hypothesis

---

## 17. 결론

Sentinel은 경쟁 제품의 장점을 다음과 같이 흡수해야 합니다.

- Polly에서 **문맥형 assistant UX**
- Loop에서 **폐쇄루프 품질 개선**
- Alyx / Phoenix에서 **trajectory intelligence와 MCP**
- Helicone에서 **가벼운 외부 assistant 연결성**

하지만 Sentinel의 진짜 승부처는 다른 곳입니다.

> **Sentinel은 분석을 잘하는 도우미가 아니라, 분석 결과를 운영 가능한 액션과 책임 있는 워크플로로 바꾸는 시스템이어야 한다.**

즉 Sentinel의 최종 정체성은 다음으로 귀결됩니다.

> **Sentinel = Governable AI Operations Control Plane**

이 문서를 기준으로 이후 개별 기능 문서는 모두 다음 질문에 답해야 합니다.

1. 이 기능은 Observe / Understand / Operate / Govern 중 어디에 속하는가?
2. 이 기능은 단순 분석을 넘어 운영 행동으로 연결되는가?
3. 이 기능은 approval / audit / policy와 어떤 관계를 가지는가?
4. 이 기능은 Web / CLI / MCP 중 몇 개의 surface에서 재사용 가능한가?

이 질문에 답하지 못하는 기능은, Sentinel의 핵심 방향과 거리가 있는 기능으로 봅니다.

---

## 18. 참고 자료

- LangSmith Polly docs  
  https://docs.langchain.com/langsmith/polly
- LangSmith Polly launch blog  
  https://blog.langchain.com/introducing-polly-your-ai-agent-engineer/
- Braintrust Loop docs  
  https://www.braintrust.dev/docs/observe/loop
- Braintrust Loop blog  
  https://www.braintrust.dev/blog/loop
- Arize Alyx 소개  
  https://arize.com/blog/meet-alyx-arizes-evolving-ai-agent/
- Arize Observe 2025 Releases  
  https://arize.com/blog/observe-2025-releases/
- Phoenix MCP server docs  
  https://arize.com/docs/phoenix/integrations/phoenix-mcp-server
- Phoenix Prompt Playground docs  
  https://arize.com/docs/phoenix/prompt-engineering/overview-prompts/prompt-playground
- Helicone MCP docs  
  https://docs.helicone.ai/integrations/tools/mcp
