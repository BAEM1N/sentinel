# WF-02 Prompt Registry + Diff + Promotion

    - 영역: Web
    - 분류: 신규기능
    - 우선순위: 높음
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    Langfuse prompt를 웹에서 조회하고, 버전 diff를 보고, staging → production 승격을 승인 기반으로 수행하는 기능입니다. 이 기능은 Sentinel을 단순 모니터링 도구에서 실제 운영 도구로 끌어올리는 핵심 축입니다.

    ## 2. 왜 필요한가

    프롬프트 운영은 LLMOps의 핵심인데, 현재는 웹 UI가 없어 agent/CLI 의존도가 높습니다. 운영자와 리뷰어가 함께 볼 수 있는 registry가 필요합니다.

    ## 3. 현재 코드 기준 진단

    - prompt 조회/저장 tool은 있지만 웹 UI가 없습니다.
- 버전 간 diff, 승격 승인, 변경 사유 기록이 없습니다.

    ### 관련 코드/근거

    - `sentinel/tools/prompt_mgmt.py:10-67`
- `sentinel/subagents.py:30-49`
- `README.md:16-18`

    ## 4. 목표 상태

    운영자가 웹에서 프롬프트를 조회·비교·승격·이력 추적할 수 있는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - prompt list/detail
- version diff
- label view(production/staging)
- promotion workflow

    ### 제외 범위
    - 완전한 visual prompt builder

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - prompt name별 버전 목록을 볼 수 있어야 합니다.
- 두 버전의 diff를 볼 수 있어야 합니다.
- staging → production promote는 승인 단계를 거쳐야 합니다.
- 변경 이유, 연관 평가 run, 관련 trace 링크를 남길 수 있어야 합니다.

    ### 비기능 요구사항
    - 민감 프롬프트는 role 기반 마스킹이 가능해야 합니다.
- diff 뷰는 대형 텍스트도 읽기 쉬워야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - 신규 라우트/템플릿
- `sentinel/tools/prompt_mgmt.py`
- approval/audit 계층과 연동

    ### 권장 디렉터리/파일 구조
    ```text
templates/
├── prompt_list.html
├── prompt_detail.html
└── prompt_diff.html
```

    ### 데이터/제어 흐름
    1. prompt 목록을 조회합니다.
2. 상세에서 버전/라벨을 확인합니다.
3. diff 화면에서 변경 내용을 검토합니다.
4. promote 요청을 생성하고 승인 후 적용합니다.

    ### API / CLI / 내부 계약 초안
    - `GET /prompts`
- `GET /prompts/{name}`
- `GET /prompts/{name}/diff?v1=...&v2=...`
- `POST /prompts/{name}/promote`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - prompt list/detail 화면 구현
- 기본 diff 뷰 추가

    ### Phase 2 — 운영 가능한 형태로 보강
    - promotion request + approval 연결
- 관련 평가 결과 링크 추가

    ### Phase 3 — 고도화
    - A/B 결과 비교와 rollback UI 추가

    ## 9. 테스트 전략

    - version diff 렌더링 테스트
- promotion 권한 테스트
- approval 없이 promote 차단 테스트

    ## 10. 리스크와 대응

    - 프롬프트 본문 자체가 민감할 수 있습니다. → role-based masking과 export 제한을 둡니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 웹에서 프롬프트 버전 운영이 가능하다.
- 승격이 승인 기반으로 통제된다.

    ## 12. 후속 확장 아이디어

    - prompt experiment board
- prompt lint
