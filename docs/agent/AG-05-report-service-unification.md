# AG-05 보고서 생성 로직 단일 서비스화

    - 영역: Agent
    - 분류: 개선
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    현재 tool, web route, scheduler에 흩어진 보고서 생성 흐름을 `ReportService` 한 곳으로 모아 기능 드리프트를 줄이고 테스트 가능한 구조로 만드는 개선입니다.

    ## 2. 왜 필요한가

    같은 기능이 여러 곳에 복제되면 작은 정책 변경도 세 군데 이상을 동시에 수정해야 합니다. 특히 기간 계산, 파일명 규칙, 알림 전송, HTML 옵션 같은 정책은 중복될수록 어긋나기 쉽습니다.

    ## 3. 현재 코드 기준 진단

    - tool `generate_report`가 자체적으로 프롬프트 생성/저장 로직을 가집니다.
- 웹 `/api/generate`도 거의 같은 내용을 다시 구현합니다.
- scheduler도 별도의 유사 구현을 가지고 있습니다.
- HTML 생성 정책이 tool/web/scheduler 경로마다 조금씩 다르게 보일 수 있습니다.

    ### 관련 코드/근거

    - `sentinel/tools/metrics.py:397-474`
- `sentinel/web/routes.py:99-175`
- `sentinel/web/scheduler.py:14-65`

    ## 4. 목표 상태

    보고서 생성은 하나의 서비스 계층만이 담당하고, tool/웹/scheduler는 이 서비스를 호출하는 thin wrapper가 되는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - ReportService 추출
- 기간 계산 정책 통일
- 파일명 정책 통일
- 알림 호출 지점 통일

    ### 제외 범위
    - 보고서 템플릿 재디자인 전체
- 새로운 보고서 종류 추가

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - 입력: period, from_ts, to_ts, output_html, notify 옵션을 받습니다.
- 출력: 생성된 파일 경로, 기간 메타데이터, 알림 결과를 구조화해 반환합니다.
- 동일 서비스가 tool/web/scheduler에서 모두 재사용되어야 합니다.
- 기본 기간 계산 규칙은 경로에 따라 달라지지 않아야 합니다.

    ### 비기능 요구사항
    - 서비스 계층은 부수효과가 적고 테스트 가능해야 합니다.
- 파일 저장과 알림 전송은 명확히 분리되어야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - 신규 `sentinel/services/report_service.py`
- `sentinel/tools/metrics.py` — service 호출형으로 축소
- `sentinel/web/routes.py`
- `sentinel/web/scheduler.py`

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
├── services/
│   └── report_service.py
├── tools/metrics.py
└── web/
    ├── routes.py
    └── scheduler.py
```

    ### 데이터/제어 흐름
    1. 호출자(tool/web/scheduler)가 ReportRequest를 만듭니다.
2. ReportService가 기간, 데이터 수집, 프롬프트 생성, 렌더링, 저장을 수행합니다.
3. 필요 시 알림 모듈을 호출합니다.
4. ReportResult를 호출자에게 반환합니다.

    ### API / CLI / 내부 계약 초안
    - `ReportRequest(period, from_ts, to_ts, output_html, notify)`
- `ReportResult(md_path, html_path, date_range, notification_results)`
- `resolve_period_range(period, now, mode)`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - 현재 공통 코드 블록을 추출해 ReportService를 만듭니다.
- tool/web/scheduler가 모두 같은 service를 쓰게 바꿉니다.
- 파일명 정책을 공통 함수로 만듭니다.

    ### Phase 2 — 운영 가능한 형태로 보강
    - 알림 전송과 파일 저장을 service 내부 서브루틴으로 분리합니다.
- 생성 결과를 구조화된 객체로 반환합니다.
- 기간 계산 정책을 단위 테스트로 고정합니다.

    ### Phase 3 — 고도화
    - 비동기 job queue와 연동 가능한 service 인터페이스로 확장합니다.
- report type(weekly executive / anomaly / release review) 추가를 쉽게 만듭니다.

    ## 9. 테스트 전략

    - tool/web/scheduler 세 경로가 같은 결과 구조를 받는지 테스트
- 기간 계산 regression 테스트
- HTML 옵션 on/off 테스트
- 알림 실패 시 결과 구조 유지 테스트

    ## 10. 리스크와 대응

    - 중복 제거 리팩터링 중 기존 동작이 깨질 수 있습니다. → 현재 동작을 golden snapshot으로 먼저 고정합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 보고서 생성 로직이 한 서비스 계층으로 수렴한다.
- tool/web/scheduler 구현이 얇아진다.
- 기간/파일명/알림 정책이 한 곳에서 관리된다.

    ## 12. 후속 확장 아이디어

    - 보고서 draft/review/publish workflow
- 다양한 report template 전략 패턴
