# AG-07 쓰기/변경 Tool에 대한 HITL 승인 계층

    - 영역: Agent
    - 분류: 개선
    - 우선순위: 높음
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    프롬프트 저장, 점수 생성, 데이터셋 수정, 주석 생성처럼 운영 데이터를 바꾸는 tool 호출에 대해 preview → approval → apply 단계의 사람 개입(HITL) 흐름을 추가하는 개선입니다.

    ## 2. 왜 필요한가

    Sentinel은 단순 조회 도구가 아니라 운영 데이터에 영향을 줄 수 있습니다. 읽기 도구와 쓰기 도구가 같은 권한으로 노출되면 실수나 잘못된 에이전트 추론이 production 데이터를 오염시킬 수 있습니다.

    ## 3. 현재 코드 기준 진단

    - prompt 저장, score 생성, dataset 생성/추가, annotation 생성이 모두 즉시 실행됩니다.
- 서브에이전트도 mutation tool을 사용할 수 있습니다.
- staging/production 승인 프로세스가 코드 차원에서 분리되어 있지 않습니다.

    ### 관련 코드/근거

    - `sentinel/tools/prompt_mgmt.py:35-48`
- `sentinel/tools/evaluation.py:39-55`
- `sentinel/tools/platform.py:42-60,97-108`
- `sentinel/subagents.py:41-48,62-69`

    ## 4. 목표 상태

    Sentinel이 운영 데이터를 바꾸기 전에 미리보기와 승인 단계를 거치고, 누가 어떤 변경을 승인했는지 남는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - mutation tool 분류
- preview payload 생성
- approval record 저장
- 적용/거부 흐름 설계

    ### 제외 범위
    - 전사 결재 시스템 연동
- 모든 업무 권한체계 완성

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - mutation 요청은 먼저 preview 상태로 생성되어야 합니다.
- production label 변경은 별도 고위험 승인 정책을 가져야 합니다.
- 승인 없이 실제 API mutation이 호출되지 않아야 합니다.
- 변경 요청의 before/after, requester, approver, timestamp가 저장되어야 합니다.

    ### 비기능 요구사항
    - 조회 경로는 가능한 한 기존 UX를 깨지 않아야 합니다.
- 감사 추적(auditability)이 확보되어야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - 신규 `sentinel/core/approvals.py`
- 신규 `sentinel/core/policies.py`
- `sentinel/tools/prompt_mgmt.py`
- `sentinel/tools/evaluation.py`
- `sentinel/tools/platform.py`

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
├── core/
│   ├── approvals.py
│   └── policies.py
└── tools/
```

    ### 데이터/제어 흐름
    1. agent가 mutation intent를 생성합니다.
2. policy engine이 위험도를 분류합니다.
3. preview payload와 approval request를 저장합니다.
4. 사람이 승인하면 실제 mutation 함수를 실행합니다.
5. 결과를 audit log에 남깁니다.

    ### API / CLI / 내부 계약 초안
    - `MutationIntent(action, target, payload, risk_level)`
- `ApprovalRequest(id, status, requester, approver, preview)`
- `apply_approved_mutation(request_id)`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - mutation tool 목록을 식별하고 read-only tool과 분리합니다.
- preview-only 실행 경로를 만듭니다.
- 승인 전 실제 mutation이 일어나지 않도록 래핑합니다.

    ### Phase 2 — 운영 가능한 형태로 보강
    - approval 저장소와 기본 CLI 승인 인터페이스를 추가합니다.
- 고위험 action(예: production prompt 저장) 정책을 따로 둡니다.

    ### Phase 3 — 고도화
    - 웹 승인함 / 알림 연동 / audit viewer를 추가합니다.
- 정책을 YAML 또는 DB 기반으로 외부화합니다.

    ## 9. 테스트 전략

    - 승인 없이 mutation 실행되지 않는지 테스트
- preview payload에 before/after 정보가 포함되는지 테스트
- 고위험 정책 분기 테스트

    ## 10. 리스크와 대응

    - 운영 속도가 느려질 수 있습니다. → 저위험 action은 auto-approve 가능 정책으로 분리합니다.
- 도구 래핑 과정에서 기존 flow가 깨질 수 있습니다. → 읽기/쓰기 도구 경계를 먼저 문서화합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - mutation tool이 approval 계층 뒤로 이동한다.
- preview/approval/apply 흐름이 구현된다.
- 누가 무엇을 승인했는지 추적 가능하다.

    ## 12. 후속 확장 아이디어

    - Slack/웹 승인 인터페이스
- 롤백 가능한 mutation 설계
