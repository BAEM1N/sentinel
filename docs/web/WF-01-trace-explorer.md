# WF-01 Trace Explorer

    - 영역: Web
    - 분류: 신규기능
    - 우선순위: 높음
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    이 기능은 Sentinel의 Observe 역량을 실제 웹 UI로 끌어올리는 핵심 기능입니다. 운영자가 name/user/session/tag/date/release/environment 기준으로 trace를 찾고, observation/score/metadata를 drilldown 할 수 있는 화면입니다.

    ## 2. 왜 필요한가

    현재 Sentinel의 강점은 trace/tool capability에 있지만, 웹에서는 거의 보고서만 볼 수 있습니다. Trace Explorer가 있어야 이 제품이 진짜 운영 콘솔처럼 보이기 시작합니다.

    ## 3. 현재 코드 기준 진단

    - trace 조회 도구는 존재하지만 웹 UI가 없습니다.
- 보고서 없이 즉시 문제 trace를 확인할 수 있는 경로가 없습니다.

    ### 관련 코드/근거

    - `sentinel/tools/traces.py:10-127`
- `README.md:11-18`
- `sentinel/web/routes.py:39-202`

    ## 4. 목표 상태

    운영자가 웹에서 trace를 검색하고, 세부 관측치와 점수, 코멘트를 확인하며, 필요한 경우 후속 액션으로 이어질 수 있는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - trace 검색 화면
- trace detail drawer/page
- session 기반 탐색
- score/annotation 표시

    ### 제외 범위
    - 완전한 Langfuse 대체 UI

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - 필터: name, user, session, tags, from/to, environment, release, version
- 목록: latency, cost, tokens, level, timestamp 요약 표시
- 상세: input/output, observation, score, metadata, annotation
- 액션: 평가 시작, 데이터셋 편입, 리뷰 요청, 보고서에 추가 등 후속 링크 제공

    ### 비기능 요구사항
    - 대용량 trace에서도 페이지가 멈추지 않아야 합니다.
- 필터 state를 URL query string으로 표현할 수 있어야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - 신규 `sentinel/web/routes_traces.py` 또는 `routes.py` 확장
- 신규 템플릿 `trace_list.html`, `trace_detail.html`
- `sentinel/tools/traces.py` 또는 shared service 계층

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
└── templates/
    ├── trace_list.html
    └── trace_detail.html
```

    ### 데이터/제어 흐름
    1. 사용자가 필터를 입력합니다.
2. 웹 라우트가 trace query를 service/tool에 전달합니다.
3. 목록 응답을 렌더링합니다.
4. 상세 페이지에서 observation/score/metadata를 drilldown 합니다.
5. 후속 action 버튼으로 다른 기능과 연결합니다.

    ### API / CLI / 내부 계약 초안
    - `GET /traces`
- `GET /traces/{trace_id}`
- `GET /sessions/{session_id}`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - trace list + 기본 필터 추가
- trace detail 페이지 추가

    ### Phase 2 — 운영 가능한 형태로 보강
    - session timeline, pagination, saved filters 추가
- annotation/score 표시 강화

    ### Phase 3 — 고도화
    - inbox/review/dataset builder와 연결
- anomaly-first 정렬 도입

    ## 9. 테스트 전략

    - 필터 query parsing 테스트
- trace detail 렌더링 테스트
- 대용량 payload에서 graceful rendering 테스트

    ## 10. 리스크와 대응

    - trace detail에 민감정보가 포함될 수 있습니다. → RBAC와 masking 옵션을 함께 설계합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 웹에서 trace를 직접 찾고 볼 수 있다.
- 보고서 없이도 문제 파악이 가능하다.

    ## 12. 후속 확장 아이디어

    - saved searches
- compare traces
