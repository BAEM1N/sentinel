# WF-09 Team RBAC 및 Multi-tenant Workspace

    - 영역: Web
    - 분류: 신규기능
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    팀 단위 운영을 지원하기 위해 사용자 역할, 프로젝트별 권한, tenant별 데이터 분리를 도입하는 장기 기능입니다.

    ## 2. 왜 필요한가

    Sentinel이 개인용 도구에서 조직용 운영 콘솔로 발전하려면 팀과 프로젝트가 늘어도 권한과 데이터가 섞이지 않아야 합니다.

    ## 3. 현재 코드 기준 진단

    - 사용자/tenant 개념이 없습니다.
- 모든 데이터가 사실상 단일 운영 공간을 전제로 합니다.

    ### 관련 코드/근거

    - `sentinel/web/routes.py:39-202`
- `sentinel/tools/platform.py:10-126`

    ## 4. 목표 상태

    tenant/project/workspace 개념이 추가되어 여러 팀이 하나의 Sentinel 인스턴스를 안전하게 공유할 수 있는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - tenant 모델
- project ACL
- role inheritance
- tenant-aware query scoping

    ### 제외 범위
    - 완전한 SaaS billing 시스템

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - 사용자는 tenant와 role을 가져야 합니다.
- 프로젝트별로 Viewer/Operator/Approver/Admin 권한이 달라질 수 있어야 합니다.
- trace/report/eval/dataset 접근은 tenant/project scope를 따라야 합니다.

    ### 비기능 요구사항
    - 기존 단일 테넌트 설치와의 호환성이 있어야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - auth/rbac 계층
- 공통 scope model
- 향후 DB 모델

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
├── auth/
├── tenancy/
└── permissions/
```

    ### 데이터/제어 흐름
    1. 요청 사용자의 tenant/project context를 식별합니다.
2. query/service 계층이 context를 강제 적용합니다.
3. UI는 허용된 프로젝트만 보여줍니다.

    ### API / CLI / 내부 계약 초안
    - `Tenant`
- `ProjectMembership`
- `enforce_scope(user, resource)`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - role model과 project membership 정의
- 단일 tenant 모드 + future-proof schema 설계

    ### Phase 2 — 운영 가능한 형태로 보강
    - tenant-aware route/query enforcement
- project switcher UI

    ### Phase 3 — 고도화
    - 완전한 multi-tenant isolation, billing, admin console

    ## 9. 테스트 전략

    - project ACL 테스트
- tenant scope isolation 테스트
- 권한 누락 시 데이터 누출 방지 테스트

    ## 10. 리스크와 대응

    - 초기 구조가 과도하게 복잡해질 수 있습니다. → 단일 tenant 호환 모드를 유지합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 팀/프로젝트 단위 권한과 데이터 경계가 존재한다.
- 민감 운영 정보가 권한 없이 노출되지 않는다.

    ## 12. 후속 확장 아이디어

    - organization admin panel
- usage billing/chargeback
