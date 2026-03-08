# WEB-01 보고서 뷰어 보안 강화

    - 영역: Web
    - 분류: 개선
    - 우선순위: 최우선
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    LLM이 생성한 Markdown/HTML 보고서를 브라우저에서 안전하게 렌더링하도록 sanitize, sandbox, CSP, 다운로드 중심 전략을 적용하는 개선입니다.

    ## 2. 왜 필요한가

    현재 보고서는 Langfuse trace 데이터와 LLM 생성물이 합쳐진 결과물입니다. 즉, 사용자가 직접 작성하지 않은 텍스트를 브라우저가 실행 가능한 형태로 받아들일 수 있는 구조이므로 XSS와 유사한 리스크가 높습니다.

    ## 3. 현재 코드 기준 진단

    - Markdown은 `marked.parse(raw)` 결과를 `innerHTML`로 주입합니다.
- HTML 보고서는 `iframe srcdoc`로 바로 렌더링되며 sandbox가 없습니다.
- 보안 헤더/CSP 설정이 없습니다.
- HTML 미리보기와 파일 다운로드가 같은 수준으로 노출되어 있습니다.

    ### 관련 코드/근거

    - `sentinel/web/routes.py:73-80`
- `sentinel/templates/report_view.html:85-99`
- `sentinel/templates/base.html:1-99`

    ## 4. 목표 상태

    웹에서 보고서를 보더라도 임의 스크립트 실행 가능성이 현저히 낮아지고, HTML 보고서는 제한된 미리보기 또는 다운로드 중심으로 제공되는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - Markdown sanitize
- iframe sandbox
- 보안 헤더/CSP
- 미리보기 정책 재정의

    ### 제외 범위
    - 전사 보안 게이트웨이

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - Markdown 렌더링은 sanitize를 거쳐야 합니다.
- HTML 보고서는 최소한 `sandbox`가 적용된 iframe에서 렌더링해야 합니다.
- 고위험 HTML은 미리보기 대신 다운로드만 허용하는 모드가 필요합니다.
- 보안 정책 위반이나 sanitize 제거 항목을 운영 로그로 남길 수 있어야 합니다.

    ### 비기능 요구사항
    - 기존 보고서 가독성이 크게 무너지지 않아야 합니다.
- CSP는 외부 자산 의존성과 함께 설계되어야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - `sentinel/web/routes.py`
- `sentinel/templates/report_view.html`
- 신규 `sentinel/web/security.py`

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
└── web/
    ├── routes.py
    ├── security.py
    └── templates/report_view.html
```

    ### 데이터/제어 흐름
    1. 보고서 파일을 읽습니다.
2. 파일 타입에 따라 markdown/html 보안 처리 전략을 선택합니다.
3. markdown은 sanitize 후 렌더링합니다.
4. html은 sandbox iframe 또는 download-only 정책으로 제공합니다.
5. 응답 헤더에 CSP와 보안 헤더를 추가합니다.

    ### API / CLI / 내부 계약 초안
    - `sanitize_markdown_html(content)`
- `build_safe_iframe_attrs()`
- `preview_policy(file_type, risk_level)`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - Markdown sanitize 도입
- iframe sandbox 적용
- 기본 보안 헤더 추가

    ### Phase 2 — 운영 가능한 형태로 보강
    - download-only 모드와 preview toggle 제공
- sanitize 제거 내역 로그 추가

    ### Phase 3 — 고도화
    - HTML report signer/validator 개념을 도입합니다.
- 위험 점수 기반 렌더링 정책을 자동화합니다.

    ## 9. 테스트 전략

    - script tag 포함 markdown 테스트
- iframe sandbox 속성 테스트
- malicious HTML 미리보기 차단 테스트

    ## 10. 리스크와 대응

    - sanitize가 레이아웃 일부를 망가뜨릴 수 있습니다. → 허용 태그/속성 allowlist를 점진적으로 조정합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 보고서 미리보기가 기본적으로 안전한 렌더링 경로를 사용한다.
- 고위험 HTML은 실행되지 않는다.

    ## 12. 후속 확장 아이디어

    - signed report artifacts
- 보안 이벤트 대시보드
