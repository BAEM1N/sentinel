# WEB-03 보고서 생성의 백그라운드 Job화

    - 영역: Web
    - 분류: 개선
    - 우선순위: 높음
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    웹 요청 안에서 바로 실행되는 LLM 기반 보고서 생성을 job queue 또는 background task로 이동해 사용자가 진행 상태를 볼 수 있게 만드는 개선입니다.

    ## 2. 왜 필요한가

    현재 `/api/generate`는 요청-응답 한 번에 데이터 수집, 모델 호출, 파일 저장, 알림 전송까지 처리합니다. 느린 LLM 호출이나 외부 API 지연이 바로 웹 응답 지연으로 이어집니다.

    ## 3. 현재 코드 기준 진단

    - `/api/generate`가 동기적으로 생성/저장/알림을 모두 수행합니다.
- 생성 중 상태를 추적하는 job model이 없습니다.
- 사용자는 redirect 후 결과만 볼 뿐 진행률이나 실패 이유를 확인하기 어렵습니다.

    ### 관련 코드/근거

    - `sentinel/web/routes.py:99-175`
- `sentinel/web/notify.py:22-140`
- `sentinel/tools/metrics.py:397-474`

    ## 4. 목표 상태

    보고서 생성 요청이 job으로 등록되고, 사용자는 job 상태를 확인하며 완료 후 보고서를 조회하는 비동기 UX를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - job 모델
- job status API
- UI 상태 페이지
- 실패/재시도 정책

    ### 제외 범위
    - 대규모 분산 큐 인프라 완성

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - 생성 요청 시 job id를 반환해야 합니다.
- job 상태는 queued/running/succeeded/failed/cancelled를 가져야 합니다.
- 성공 시 생성된 artifact 경로를 연결해야 합니다.
- 실패 사유와 재시도 가능 여부를 보여줘야 합니다.

    ### 비기능 요구사항
    - 웹 요청은 빠르게 반환되어야 합니다.
- job 상태 저장은 재시작 후에도 최대한 유지되어야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - 신규 `sentinel/jobs/`
- `sentinel/web/routes.py`
- `sentinel/services/report_service.py` (추가 예정)

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
├── jobs/
│   ├── models.py
│   ├── queue.py
│   └── workers.py
└── web/routes.py
```

    ### 데이터/제어 흐름
    1. 사용자가 보고서 생성 폼을 제출합니다.
2. 서버는 job을 등록하고 job id를 반환합니다.
3. worker가 ReportService를 호출해 생성합니다.
4. UI는 job status endpoint를 polling하거나 SSE로 구독합니다.
5. 완료 시 artifact 링크와 알림 결과를 표시합니다.

    ### API / CLI / 내부 계약 초안
    - `POST /api/generate-jobs`
- `GET /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/retry`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - in-process background task로 시작합니다.
- job model과 status API를 추가합니다.
- UI에 진행 상태를 표시합니다.

    ### Phase 2 — 운영 가능한 형태로 보강
    - 외부 queue(RQ/Celery/Arq 등) 연동을 고려합니다.
- 실패/재시도/취소 기능을 넣습니다.

    ### Phase 3 — 고도화
    - 우선순위 큐, 예약 실행, 배치 실행을 지원합니다.

    ## 9. 테스트 전략

    - job 생성/상태 전이 테스트
- 실패 시 status/에러 메시지 테스트
- 성공 시 artifact 링크 연결 테스트

    ## 10. 리스크와 대응

    - 초기 in-process background task는 완전한 신뢰성을 주지 못합니다. → Phase 2에서 영속 queue로 전환합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 웹 요청이 빠르게 반환된다.
- 사용자가 생성 상태를 추적할 수 있다.
- 실패 이유와 재시도 경로가 보인다.

    ## 12. 후속 확장 아이디어

    - batch job monitor
- job priority controls
