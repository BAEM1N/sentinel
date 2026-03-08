# AG-04 도구 출력의 구조화 및 스키마화

    - 영역: Agent
    - 분류: 개선
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    현재 문자열(JSON 텍스트) 중심인 tool 반환 값을 구조화된 스키마로 전환하여 agent reasoning의 안정성과 후속 UI/API 재사용성을 높이는 개선입니다.

    ## 2. 왜 필요한가

    에이전트가 다시 문자열을 읽고 해석해야 하는 구조는 토큰 낭비와 파싱 불안정성을 동시에 키웁니다. 또한 같은 데이터를 웹 UI, 배치 작업, 테스트 코드에서 재사용하기 어렵습니다.

    ## 3. 현재 코드 기준 진단

    - trace/session/score/dataset 관련 도구가 대부분 JSON 문자열을 반환합니다.
- 실패/성공 포맷이 섞여 있어 상위 계층이 포맷을 신뢰하기 어렵습니다.
- 대형 payload를 summary 없이 모두 문자열로 반환하려는 경향이 있습니다.

    ### 관련 코드/근거

    - `sentinel/tools/traces.py:45-106`
- `sentinel/tools/evaluation.py:23-36`
- `sentinel/tools/metrics.py:82-83`
- `sentinel/tools/platform.py:29-126`

    ## 4. 목표 상태

    tool 출력이 명시적 schema를 가지며, 에이전트/웹/API/테스트에서 동일한 데이터 계약을 재사용할 수 있는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - 응답 모델 정의
- 성공/실패 envelope 표준화
- summary + detail 구조 도입
- pagination 메타데이터 포함

    ### 제외 범위
    - 모든 tool을 한 번에 완벽 교체
- ORM/DB 모델 도입

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - tool 응답은 최소한 `status`, `data`, `meta`, `error` 구조를 가져야 합니다.
- list 계열 응답에는 `page`, `limit`, `count`, `has_more`가 들어가야 합니다.
- 대용량 trace detail은 summary 필드와 raw field를 분리해야 합니다.
- CLI/웹에서 동일 응답을 직렬화하여 활용할 수 있어야 합니다.

    ### 비기능 요구사항
    - schema는 테스트 가능하고 IDE 지원이 쉬운 형태여야 합니다.
- 기존 agent 프롬프트를 한 번에 깨지 않도록 점진적 마이그레이션이 가능해야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - 신규 `sentinel/schema/` 또는 `sentinel/models/`
- `sentinel/tools/*.py`
- `main.py` — `--json` 출력 연동 시 유리
- 향후 `sentinel/web/routes.py` JSON API 재사용 기반

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
├── schema/
│   ├── common.py
│   ├── traces.py
│   ├── reports.py
│   └── evaluation.py
└── tools/
```

    ### 데이터/제어 흐름
    1. tool이 외부 API에서 원시 데이터를 받습니다.
2. schema 계층이 원시 데이터를 내부 응답 모델로 매핑합니다.
3. 상위 에이전트나 웹 계층은 이 모델을 직렬화해서 사용합니다.
4. 필요 시 human-readable summary는 별도 필드로 제공합니다.

    ### API / CLI / 내부 계약 초안
    - `ToolResult[T]` generic envelope
- `TraceSummary`, `TraceDetail`, `ScoreSummary`, `DatasetItemSummary`
- `PaginatedResult[T]`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - 공통 envelope와 trace/score 계열 스키마부터 정의합니다.
- 기존 문자열 반환을 유지하되 내부적으로 schema를 먼저 생성하게 바꿉니다.
- 테스트 코드를 schema 기준으로 작성합니다.

    ### Phase 2 — 운영 가능한 형태로 보강
    - 평가/보고서/플랫폼 도구까지 확장합니다.
- CLI JSON 출력과 연계합니다.
- 웹 JSON API 설계 시 같은 schema를 재사용합니다.

    ### Phase 3 — 고도화
    - tool layer에서 직접 Pydantic schema serialization을 사용합니다.
- OpenAPI 또는 내부 문서 자동 생성까지 연결합니다.

    ## 9. 테스트 전략

    - schema validation 테스트
- list result pagination 메타데이터 테스트
- 성공/실패 envelope 일관성 테스트

    ## 10. 리스크와 대응

    - 초기에는 문자열 consumer와 schema consumer가 공존해 복잡할 수 있습니다. → 어댑터 계층을 둡니다.
- LLM agent가 긴 JSON을 그대로 읽으면 토큰이 늘 수 있습니다. → summary 필드를 병행합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 핵심 tool 응답이 공통 envelope로 정리되어 있다.
- 테스트와 문서가 문자열 포맷이 아닌 schema를 기준으로 작성된다.

    ## 12. 후속 확장 아이디어

    - 웹 API와 CLI에 공통 schema 재사용
- 내부 SDK 형태로 분리
