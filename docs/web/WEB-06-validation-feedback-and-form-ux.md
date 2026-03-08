# WEB-06 입력 검증 및 생성 피드백 UX

    - 영역: Web
    - 분류: 개선
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    보고서 생성 폼과 API에 날짜/period 검증, 에러 메시지, 성공 피드백, 알림 결과 표시 등을 추가하는 개선입니다.

    ## 2. 왜 필요한가

    지금은 사용자가 잘못된 기간을 넣거나 생성이 실패해도 redirect 뒤에 이유를 파악하기 어렵습니다. 운영용 UI라면 결과와 실패 원인을 설명해야 합니다.

    ## 3. 현재 코드 기준 진단

    - period/from_date/to_date가 raw string으로 들어옵니다.
- 생성 후 `/reports`로 redirect만 하며 결과 메시지가 없습니다.
- 알림 전송 성공/실패가 UI에 노출되지 않습니다.

    ### 관련 코드/근거

    - `sentinel/web/routes.py:99-175`
- `sentinel/templates/index.html:27-55`
- `sentinel/templates/reports.html:12-45`
- `sentinel/web/notify.py:131-140`

    ## 4. 목표 상태

    사용자가 잘못된 입력을 즉시 수정할 수 있고, 생성 성공/실패/알림 결과를 명확히 이해할 수 있는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - request validation
- flash message 또는 status view
- field-level error
- 알림 결과 표시

    ### 제외 범위
    - 완전한 프론트엔드 SPA

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - from_date > to_date는 차단해야 합니다.
- 지원하지 않는 period는 validation에서 걸러야 합니다.
- 성공 메시지에는 생성 파일과 알림 채널 결과가 포함돼야 합니다.
- 실패 메시지는 사람이 이해할 수 있어야 합니다.

    ### 비기능 요구사항
    - HTML form과 JSON API 양쪽에서 재사용 가능한 validation 계층이 필요합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - 신규 `sentinel/web/forms.py` 또는 `schemas.py`
- `sentinel/web/routes.py`
- `sentinel/templates/index.html`
- `sentinel/templates/reports.html`

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
└── web/
    ├── schemas.py
    ├── routes.py
    └── templates/
```

    ### 데이터/제어 흐름
    1. 폼 제출 시 validation schema가 먼저 입력을 검증합니다.
2. 유효하지 않으면 같은 페이지에 field error를 다시 렌더링합니다.
3. 유효하면 생성 job 또는 service를 실행합니다.
4. 완료 후 상태 메시지와 artifact 링크, notification result를 보여줍니다.

    ### API / CLI / 내부 계약 초안
    - `ReportGenerateForm`
- `FlashMessage(level, title, detail)`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - validation schema 도입
- 기본 성공/실패 메시지 표시
- 알림 결과 표시

    ### Phase 2 — 운영 가능한 형태로 보강
    - field-level error 렌더링
- JSON API와 HTML form 응답 분리

    ### Phase 3 — 고도화
    - 작업 큐 상태 페이지와 연결
- 사용자별 최근 요청 히스토리 표시

    ## 9. 테스트 전략

    - 날짜 역전 validation 테스트
- 잘못된 period 테스트
- 성공/실패 메시지 렌더링 테스트

    ## 10. 리스크와 대응

    - 서버 렌더링 구조에서는 flash message 관리가 번거로울 수 있습니다. → 최소 세션 기반 또는 query param 기반으로 시작합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 잘못된 입력이 사전에 차단된다.
- 사용자가 생성 결과와 실패 이유를 확인할 수 있다.

    ## 12. 후속 확장 아이디어

    - SSE 기반 실시간 진행 상태
