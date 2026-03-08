# AF-01 Persistent Run History 및 Audit Log

    - 영역: Agent
    - 분류: 신규기능
    - 우선순위: 높음
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    Sentinel agent가 어떤 질의를 받아 어떤 도구를 호출했고, 어떤 변경을 시도/승인/실패했는지를 영속 저장소에 남기는 기능입니다. 이 기능은 개선점이 아니라 제품 신뢰도를 높이는 핵심 기능 후보입니다.

    ## 2. 왜 필요한가

    운영 도구는 “결과”만큼 “과정”이 중요합니다. 문제가 생겼을 때 원인을 추적하려면 실행 이력, tool call, 승인 내역, 실패 사유가 남아 있어야 합니다.

    ## 3. 현재 코드 기준 진단

    - 실행 이력이 메모리 또는 stdout 수준에 머뭅니다.
- mutation 작업의 before/after와 승인 흐름이 별도로 저장되지 않습니다.
- 운영자가 특정 날짜에 무엇이 변경되었는지 되짚기 어렵습니다.

    ### 관련 코드/근거

    - `sentinel/agent.py:38-45`
- `main.py:22-80`
- `sentinel/tools/prompt_mgmt.py:35-48`
- `sentinel/tools/platform.py:42-60,97-108`

    ## 4. 목표 상태

    실행, 도구 호출, 승인, 실패, 산출물 경로가 모두 영속 이력으로 남고, 나중에 CLI나 웹에서 조회 가능한 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - run history 모델
- tool call log
- approval/audit event 저장
- 간단한 조회 API/CLI

    ### 제외 범위
    - SIEM 전체 연동
- 장기 보존 스토리지 정책 완성

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - 각 실행마다 run_id가 생성되어야 합니다.
- 질의 내용, 주요 tool call, 결과 상태, 생성된 파일 경로가 기록되어야 합니다.
- mutation 계열은 before/after, requester, approver를 남겨야 합니다.
- 필요 시 특정 run을 재현(replay)할 수 있는 최소 메타데이터가 있어야 합니다.

    ### 비기능 요구사항
    - 개인정보/민감정보 마스킹 정책이 필요합니다.
- 로그가 과도하게 커지지 않도록 payload 저장 수준을 분리해야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - 신규 `sentinel/history/`
- 신규 `sentinel/audit/`
- `main.py`, `sentinel/agent.py`, mutation tool들

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
├── history/
│   ├── models.py
│   ├── store.py
│   └── queries.py
└── audit/
    └── events.py
```

    ### 데이터/제어 흐름
    1. 새 run이 시작될 때 run_id를 발급합니다.
2. tool call 전후 이벤트를 기록합니다.
3. mutation/approval 이벤트는 별도 audit stream으로 남깁니다.
4. run 종료 시 최종 상태와 산출물을 연결합니다.

    ### API / CLI / 내부 계약 초안
    - `RunRecord`
- `ToolCallRecord`
- `AuditEvent`
- `list_runs(filters)`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - run/tool call 저장 모델을 만듭니다.
- CLI 실행에 run_id를 부여합니다.
- 핵심 mutation 이벤트를 기록합니다.

    ### Phase 2 — 운영 가능한 형태로 보강
    - run 조회 CLI를 추가합니다.
- 보고서 파일과 run record를 연결합니다.

    ### Phase 3 — 고도화
    - 웹 이력 화면과 drilldown UI를 추가합니다.
- replay 또는 compare run 기능을 검토합니다.

    ## 9. 테스트 전략

    - run 생성/종료 기록 테스트
- tool call capture 테스트
- audit event completeness 테스트

    ## 10. 리스크와 대응

    - 민감한 prompt/trace 내용이 그대로 기록될 수 있습니다. → 마스킹 레벨을 설정으로 제공합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 각 실행에 대한 영속 이력이 남는다.
- mutation에 대한 감사 추적이 가능하다.
- 운영자가 특정 실행을 나중에 조회할 수 있다.

    ## 12. 후속 확장 아이디어

    - run diff 비교
- incident timeline export
