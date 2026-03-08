# WEB-09 정적 자산 파이프라인 및 CSP 친화화

    - 영역: Web
    - 분류: 개선
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    외부 CDN에 의존하는 Tailwind/폰트 자산을 정리하고 self-hosting 또는 빌드 산출물 방식으로 전환해 CSP를 강하게 적용할 수 있도록 만드는 개선입니다.

    ## 2. 왜 필요한가

    현재 웹 UI는 CDN 스크립트와 외부 폰트에 의존합니다. 내부망, 폐쇄망, 보안 민감 환경에서는 이런 방식이 바로 제약 조건이 됩니다.

    ## 3. 현재 코드 기준 진단

    - Tailwind CDN script를 씁니다.
- 외부 Pretendard font CDN을 사용합니다.
- CSP를 강하게 걸기 어렵습니다.

    ### 관련 코드/근거

    - `sentinel/templates/base.html:7-8`
- `sentinel/report_template.html:7`

    ## 4. 목표 상태

    웹 UI가 외부 CDN 없이도 동작하거나 최소한 대체 가능하며, CSP를 강하게 적용할 수 있는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - 정적 CSS 빌드 전략
- 폰트 self-hosting
- CSP 정책 설계
- fallback 자산 전략

    ### 제외 범위
    - 대규모 프런트엔드 빌드 시스템 전환

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - 기본 UI는 로컬 자산만으로도 렌더링 가능해야 합니다.
- CSP를 적용해 inline script 의존성을 줄여야 합니다.
- 보고서 HTML 템플릿도 동일한 자산 정책을 따라야 합니다.

    ### 비기능 요구사항
    - 빌드 파이프라인이 너무 무거워지지 않아야 합니다.
- 오프라인/폐쇄망 환경에서도 동작 가능해야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - `sentinel/templates/base.html`
- `sentinel/report_template.html`
- 신규 `static/` 또는 빌드 아웃풋 디렉터리

    ### 권장 디렉터리/파일 구조
    ```text
static/
├── css/
│   └── app.css
└── fonts/
    └── pretendard.woff2
```

    ### 데이터/제어 흐름
    1. 디자인 토큰을 정적 CSS로 컴파일합니다.
2. 템플릿은 로컬 정적 자산을 참조합니다.
3. CSP 헤더를 추가하고 inline script를 제거하거나 nonce 처리합니다.

    ### API / CLI / 내부 계약 초안
    - `/static/...` serving
- `build-css` step

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - 외부 CDN 의존성을 문서화하고 대체 자산을 준비합니다.
- 로컬 CSS/폰트 참조를 추가합니다.

    ### Phase 2 — 운영 가능한 형태로 보강
    - inline script 제거 및 CSP 설계
- 정적 파일 서빙 구성 추가

    ### Phase 3 — 고도화
    - 디자인 시스템/테마 분리

    ## 9. 테스트 전략

    - 정적 자산 경로 테스트
- CSP 헤더 존재 테스트
- 오프라인 렌더링 smoke test

    ## 10. 리스크와 대응

    - Tailwind CDN 제거 시 초기 스타일링 손실이 있을 수 있습니다. → 현재 사용 클래스 기반으로 최소 CSS부터 추출합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 외부 CDN 없이도 기본 UI가 동작한다.
- CSP를 실질적으로 적용할 수 있다.

    ## 12. 후속 확장 아이디어

    - 다크모드
- 테마 시스템
