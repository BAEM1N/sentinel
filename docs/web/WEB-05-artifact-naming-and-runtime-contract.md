# WEB-05 산출물 파일명 정책 및 런타임 계약 정리

    - 영역: Web
    - 분류: 개선
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    보고서 파일명 충돌 방지, 실행 엔트리포인트 정리, 경로 정책 명확화를 위한 개선입니다.

    ## 2. 왜 필요한가

    같은 기간 보고서를 다시 생성하면 덮어쓰기 되는 구조는 운영 기록을 잃게 만들 수 있습니다. 또한 package script와 실제 실행 계약이 어긋나면 배포 혼란이 생깁니다.

    ## 3. 현재 코드 기준 진단

    - 파일명이 `{period}_report_{from_date}` 중심입니다.
- 같은 기간 재실행 시 덮어쓸 가능성이 높습니다.
- `pyproject.toml`의 `sentinel-server = "server:app"`는 console script 관점에서 어색합니다.

    ### 관련 코드/근거

    - `sentinel/web/routes.py:144-167`
- `sentinel/web/scheduler.py:35-60`
- `pyproject.toml:31-33`

    ## 4. 목표 상태

    보고서 산출물이 고유 식별 가능한 파일명과 메타데이터를 가지며, CLI/서버/스케줄러의 실행 계약이 명확한 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - 고유 파일명 규칙
- 메타데이터 sidecar 또는 frontmatter
- server entrypoint 정리

    ### 제외 범위
    - 객체 스토리지 이관 전체

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - 파일명은 period, range, generated_at 또는 run_id를 포함해야 합니다.
- 같은 날짜 범위를 여러 번 생성해도 충돌하지 않아야 합니다.
- 실행 entrypoint는 CLI 함수 기준으로 정리되어야 합니다.

    ### 비기능 요구사항
    - 사람이 읽기 쉬운 파일명이어야 합니다.
- 자동화 스크립트도 parsing 가능해야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - `sentinel/web/routes.py`
- `sentinel/web/scheduler.py`
- `sentinel/tools/metrics.py`
- `pyproject.toml`

    ### 권장 디렉터리/파일 구조
    ```text
reports/
├── 2026-03-08_daily_2026-03-07_run-abc123.md
├── 2026-03-08_daily_2026-03-07_run-abc123.html
└── 2026-03-08_daily_2026-03-07_run-abc123.meta.json
```

    ### 데이터/제어 흐름
    1. 보고서 생성 요청 시 run_id 또는 timestamp를 발급합니다.
2. 공통 filename builder가 md/html/meta 파일명을 계산합니다.
3. 웹 목록은 meta 또는 stat 정보를 통해 표시합니다.

    ### API / CLI / 내부 계약 초안
    - `build_report_filenames(request, run_id)`
- `ReportArtifactMeta`
- `run_server()` callable for console script

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - 파일명에 generated_at 또는 run_id를 추가합니다.
- server 실행용 함수형 entrypoint를 만듭니다.

    ### Phase 2 — 운영 가능한 형태로 보강
    - report meta sidecar를 도입합니다.
- 목록 화면에서 meta 기반 정렬/필터를 적용합니다.

    ### Phase 3 — 고도화
    - report storage abstraction을 넣어 로컬 파일 외 저장소를 지원합니다.

    ## 9. 테스트 전략

    - 동일 범위 재생성 시 파일 충돌 방지 테스트
- filename builder snapshot 테스트
- console script entrypoint 테스트

    ## 10. 리스크와 대응

    - 기존 파일명과의 호환성이 필요합니다. → 과거 파일도 읽을 수 있는 backward compatible parser를 둡니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 보고서 재생성 시 충돌이 발생하지 않는다.
- 실행 entrypoint가 문서와 일치한다.

    ## 12. 후속 확장 아이디어

    - artifact versioning
- signed metadata
