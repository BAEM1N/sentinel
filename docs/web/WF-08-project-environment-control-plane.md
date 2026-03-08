# WF-08 Project / Environment Control Plane

    - 영역: Web
    - 분류: 신규기능
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    프로젝트, environment, release, version 단위로 LLMOps 운영 데이터를 나눠서 보는 공통 control plane 기능입니다.

    ## 2. 왜 필요한가

    실제 운영은 하나의 LLM 앱만 보지 않습니다. production/staging/canary 또는 제품 A/B 단위로 비교할 수 있어야 운영 콘솔로서 가치가 생깁니다.

    ## 3. 현재 코드 기준 진단

    - tool 수준에서는 확장 가능성이 있으나 UI/공통 filter model이 없습니다.
- 프로젝트/환경 스위처가 없습니다.

    ### 관련 코드/근거

    - `skills/langfuse-ops/SKILL.md:53-67`
- `sentinel/tools/traces.py:11-19`
- `sentinel/tools/metrics.py:24-33`

    ## 4. 목표 상태

    모든 주요 화면이 project/environment/release 스코프를 공유하고 비교 가능한 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - 전역 필터 스코프
- 환경 비교
- release compare
- 공통 breadcrumb/context bar

    ### 제외 범위
    - 멀티테넌트 전체 아키텍처 완성

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - 전역 스코프 선택기(project/environment/release)가 필요합니다.
- trace/report/eval/alert 화면이 이 스코프를 공유해야 합니다.
- 두 release 또는 두 environment 비교 뷰가 있어야 합니다.

    ### 비기능 요구사항
    - URL 공유 시 스코프가 보존되어야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - 공통 web context/state
- 모든 주요 routes/templates
- tool query layer 확장

    ### 권장 디렉터리/파일 구조
    ```text
templates/
├── partials/context_bar.html
└── compare_release.html
```

    ### 데이터/제어 흐름
    1. 사용자가 전역 스코프를 선택합니다.
2. 모든 쿼리가 이 스코프를 기본 필터로 사용합니다.
3. 비교 화면에서는 두 스코프를 나란히 조회합니다.

    ### API / CLI / 내부 계약 초안
    - `ContextScope(project, environment, release, version)`
- `resolve_scope_from_request()`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - 전역 context bar 추가
- trace/report 화면에 스코프 필터 적용

    ### Phase 2 — 운영 가능한 형태로 보강
    - release compare 화면 추가
- saved scopes 지원

    ### Phase 3 — 고도화
    - tenant/project ACL과 연결

    ## 9. 테스트 전략

    - scope propagation 테스트
- compare query 테스트
- URL query persistence 테스트

    ## 10. 리스크와 대응

    - 초기에는 데이터 모델이 부족할 수 있습니다. → scope는 optional로 시작하고 점진 확장합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 환경/릴리스/프로젝트 관점 운영이 가능하다.
- 주요 화면이 동일 스코프 모델을 공유한다.

    ## 12. 후속 확장 아이디어

    - cross-project executive dashboard
