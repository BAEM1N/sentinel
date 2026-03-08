# WEB-04 인증 및 RBAC 기반 추가

    - 영역: Web
    - 분류: 개선
    - 우선순위: 높음
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    현재 공개 노출 시 무방비인 웹 인터페이스에 최소 인증과 역할별 권한 구분을 도입하는 개선입니다.

    ## 2. 왜 필요한가

    보고서 생성, 프롬프트 변경 승인, 데이터셋/평가 관리 같은 기능이 확장될수록 인증과 권한은 선택이 아니라 기본 요건이 됩니다.

    ## 3. 현재 코드 기준 진단

    - 웹 라우트에 인증 계층이 없습니다.
- 누가 무엇을 볼 수 있고 실행할 수 있는지 정의가 없습니다.
- 향후 mutation approval, review inbox 같은 기능을 올리기 위한 사용자 모델도 없습니다.

    ### 관련 코드/근거

    - `sentinel/web/app.py:29-48`
- `sentinel/web/routes.py:39-202`

    ## 4. 목표 상태

    최소한 로그인된 사용자만 UI와 API에 접근하고, Viewer/Operator/Approver/Admin 역할이 분리되는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - 기본 인증 방식 정의
- 사용자/역할 모델
- 라우트 권한 데코레이터/미들웨어
- 감사 로그와 연결

    ### 제외 범위
    - 기업 SSO 전체 구현

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - 최소 Basic Auth 또는 session auth가 필요합니다.
- 역할별로 페이지/액션 접근이 달라야 합니다.
- 승인 기능과 mutation 기능은 Viewer 권한으로 접근되면 안 됩니다.
- API와 HTML 페이지 모두 같은 권한 모델을 사용해야 합니다.

    ### 비기능 요구사항
    - 로컬 단독 사용자를 위한 단순 모드와 팀용 모드를 분리해야 합니다.
- 로그인 실패/권한 부족 로그가 남아야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - 신규 `sentinel/web/auth.py`
- 신규 `sentinel/web/permissions.py`
- `sentinel/web/routes.py`

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
└── web/
    ├── auth.py
    ├── permissions.py
    └── routes.py
```

    ### 데이터/제어 흐름
    1. 요청이 들어오면 인증 미들웨어가 사용자를 식별합니다.
2. 권한 계층이 route/action별 접근 가능 여부를 판단합니다.
3. 실행 결과는 audit log와 연결됩니다.

    ### API / CLI / 내부 계약 초안
    - `User(role, identity)`
- `require_role("operator")`
- `get_current_user(request)`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - Basic Auth 또는 단순 session auth 도입
- Viewer/Operator/Admin 최소 3역할 정의

    ### Phase 2 — 운영 가능한 형태로 보강
    - Approver 역할과 approval workflow 연계
- 감사 로그와 사용자 식별 연결

    ### Phase 3 — 고도화
    - OIDC/SSO 연동
- 프로젝트 단위 RBAC 확장

    ## 9. 테스트 전략

    - 권한 없는 접근 차단 테스트
- 역할별 허용/거부 매트릭스 테스트
- API와 HTML 페이지 모두 인증 적용 테스트

    ## 10. 리스크와 대응

    - 로컬 사용자의 진입장벽이 높아질 수 있습니다. → `AUTH_MODE=disabled|basic|sso` 식 옵션을 둡니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 웹 인터페이스가 최소 인증 뒤에 있다.
- 민감 액션은 역할 기반으로 제한된다.

    ## 12. 후속 확장 아이디어

    - 세분화된 project-level RBAC
- team onboarding
