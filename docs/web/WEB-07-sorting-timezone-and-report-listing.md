# WEB-07 정렬, 시간대, 보고서 목록 정책 정리

    - 영역: Web
    - 분류: 개선
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    Recent Reports의 실제 정렬 기준, 수정 시각 표시, scheduler timezone, 기간 표기 정책을 일관되게 정리하는 개선입니다.

    ## 2. 왜 필요한가

    운영 UI에서 시간대와 정렬 기준은 생각보다 자주 혼동을 만듭니다. 지금처럼 파일명 정렬과 UTC 내부 계산이 섞여 있으면 사용자는 “왜 최신 보고서가 안 보이지?” 같은 경험을 하게 됩니다.

    ## 3. 현재 코드 기준 진단

    - 파일 목록이 filename 기준으로 정렬됩니다.
- UI 문구는 “Recent Reports”지만 실제로는 최근 수정순이 아닐 수 있습니다.
- scheduler는 UTC 기준 계산을 쓰지만 UI에는 timezone이 드러나지 않습니다.

    ### 관련 코드/근거

    - `sentinel/web/routes.py:15-32`
- `sentinel/templates/index.html:57-95`
- `sentinel/web/scheduler.py:68-103`
- `sentinel/templates/scheduler.html:41-57`

    ## 4. 목표 상태

    보고서 목록과 스케줄 정보가 사용자 관점에서 예측 가능한 시간 표현을 가지는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - modified time 정렬
- timezone 설정
- UI 표기 규칙
- range label 일관화

    ### 제외 범위
    - 완전한 국제화(i18n)

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - Recent Reports는 실제 수정시각 내림차순이어야 합니다.
- scheduler 페이지에 timezone이 명시되어야 합니다.
- 보고서 상세와 목록에서 동일한 기간 표기 포맷을 사용해야 합니다.

    ### 비기능 요구사항
    - timezone은 설정 가능해야 하되 기본값이 분명해야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - `sentinel/web/routes.py`
- `sentinel/web/scheduler.py`
- `sentinel/templates/index.html`
- `sentinel/templates/reports.html`
- `sentinel/templates/scheduler.html`

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
└── web/
    ├── time.py
    ├── routes.py
    ├── scheduler.py
    └── templates/
```

    ### 데이터/제어 흐름
    1. 보고서 메타정보를 읽을 때 stat 또는 meta 파일에서 생성시각을 가져옵니다.
2. timezone helper가 표시용 시각을 변환합니다.
3. 목록과 상세, scheduler 화면에서 공통 formatter를 사용합니다.

    ### API / CLI / 내부 계약 초안
    - `format_datetime(dt, tz, style)`
- `sort_reports(reports, key="modified")`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - modified 기준 정렬로 변경
- scheduler UI에 timezone 표기 추가

    ### Phase 2 — 운영 가능한 형태로 보강
    - 공통 time formatter 도입
- 환경변수 기반 timezone 설정 추가

    ### Phase 3 — 고도화
    - 사용자별 timezone preference 지원

    ## 9. 테스트 전략

    - 정렬 기준 테스트
- timezone formatting 테스트
- scheduler next_run 표시 테스트

    ## 10. 리스크와 대응

    - 파일 stat과 메타파일 시간이 다를 수 있습니다. → 생성시각 source of truth를 meta로 통일합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - Recent Reports가 실제 최근순으로 보인다.
- 시간대 표기가 명확하다.

    ## 12. 후속 확장 아이디어

    - 사용자 locale/timezone 설정
