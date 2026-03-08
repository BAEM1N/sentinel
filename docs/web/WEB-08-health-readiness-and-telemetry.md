# WEB-08 Health / Readiness / Telemetry 엔드포인트

    - 영역: Web
    - 분류: 개선
    - 우선순위: 높음
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    배포와 운영 자동화를 위해 `/health`, `/ready`, `/metrics` 같은 운영 엔드포인트와 구조화 로그/기초 메트릭을 추가하는 개선입니다.

    ## 2. 왜 필요한가

    서비스는 “실행 중인가?”와 “실제 요청 처리 준비가 되었는가?”가 다릅니다. 운영 플랫폼은 이 차이를 health/readiness로 판단합니다. 현재 Sentinel에는 이런 기준점이 없습니다.

    ## 3. 현재 코드 기준 진단

    - 운영 엔드포인트가 없습니다.
- 로그가 주로 print 기반입니다.
- scheduler, Langfuse, storage 준비 상태를 외부에서 확인하기 어렵습니다.

    ### 관련 코드/근거

    - `sentinel/web/routes.py:39-202`
- `sentinel/web/app.py:20-26`
- `sentinel/web/scheduler.py:63-65`

    ## 4. 목표 상태

    배포 시스템, 모니터링 시스템, 운영자가 서비스 상태를 표준 방식으로 확인할 수 있는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - health endpoint
- readiness endpoint
- 기초 metrics
- 구조화 로그 도입

    ### 제외 범위
    - 완전한 observability stack 구축

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - `/health`는 프로세스 생존 여부를 반환해야 합니다.
- `/ready`는 Langfuse/모델/스토리지/스케줄러 상태를 확인해야 합니다.
- `/metrics`는 최소한 job count, report generate count, notification success/fail 등을 포함할 수 있어야 합니다.

    ### 비기능 요구사항
    - health check는 가볍고 빠르게 응답해야 합니다.
- readiness는 외부 의존성 검사 때문에 timeout과 캐시 전략이 필요합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - `sentinel/web/routes.py`
- 신규 `sentinel/web/health.py`
- 신규 `sentinel/core/logging.py`

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
├── core/logging.py
└── web/
    ├── health.py
    └── routes.py
```

    ### 데이터/제어 흐름
    1. `/health`는 프로세스 수준의 간단한 응답을 반환합니다.
2. `/ready`는 dependency checker를 호출합니다.
3. `/metrics`는 누적 카운터/게이지를 노출합니다.
4. 구조화 로그는 request_id, job_id, run_id 중심으로 남깁니다.

    ### API / CLI / 내부 계약 초안
    - `GET /health`
- `GET /ready`
- `GET /metrics`
- `check_dependencies()`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - /health, /ready 추가
- print를 logger 호출로 일부 전환

    ### Phase 2 — 운영 가능한 형태로 보강
    - Prometheus 형식 또는 JSON metrics 노출
- request/job correlation id 도입

    ### Phase 3 — 고도화
    - OpenTelemetry 연동
- 대시보드/알람 룰 연결

    ## 9. 테스트 전략

    - health endpoint 200 테스트
- 외부 의존성 실패 시 readiness 실패 테스트
- metrics 카운터 증가 테스트

    ## 10. 리스크와 대응

    - readiness가 너무 무거우면 오히려 장애를 만들 수 있습니다. → cache/timeout 사용.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 운영 시스템이 Sentinel 상태를 표준 방식으로 확인할 수 있다.
- 로그가 구조화되어 있다.

    ## 12. 후속 확장 아이디어

    - SLO dashboard
- auto-remediation hooks
