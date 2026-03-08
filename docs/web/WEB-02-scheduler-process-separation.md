# WEB-02 웹 서버와 스케줄러 프로세스 분리

    - 영역: Web
    - 분류: 개선
    - 우선순위: 높음
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    FastAPI 앱 lifespan에 붙어 있는 scheduler를 별도 worker/command로 분리하여 중복 실행과 배포 리스크를 줄이는 개선입니다.

    ## 2. 왜 필요한가

    현재 구조에서는 웹 앱이 뜨면 scheduler도 같이 시작됩니다. 개발 reload, multi-worker, scale-out 배포에서는 같은 잡이 여러 번 실행될 수 있어 운영 사고로 바로 이어질 수 있습니다.

    ## 3. 현재 코드 기준 진단

    - 앱 startup 시 scheduler가 자동 시작됩니다.
- 개발 서버가 reload로 뜰 때 중복 실행 위험이 있습니다.
- 프로덕션에서 worker 수가 늘면 job이 중복 실행될 수 있습니다.

    ### 관련 코드/근거

    - `sentinel/web/app.py:15-26`
- `server.py:15-17`
- `sentinel/web/scheduler.py:98-103`

    ## 4. 목표 상태

    웹 서버는 웹 요청만 처리하고, 스케줄러는 별도 프로세스/커맨드/서비스로 실행되는 구조를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - scheduler worker entrypoint
- 웹 앱에서 자동 시작 제거 또는 옵션화
- 운영 문서/배포 가이드 보강

    ### 제외 범위
    - 분산 job scheduler 전체 도입

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - 웹 앱을 띄워도 scheduler가 기본 자동 실행되지 않아야 합니다.
- 별도 커맨드로 scheduler를 실행할 수 있어야 합니다.
- 스케줄러 상태 조회는 웹에서 읽기 전용으로 제공될 수 있어야 합니다.

    ### 비기능 요구사항
    - 단일 호스트 개발 편의성을 해치지 않도록 `--with-scheduler` 같은 옵션도 고려해야 합니다.
- 프로덕션 배포 문서가 분명해야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - `sentinel/web/app.py`
- `sentinel/web/scheduler.py`
- `server.py`
- 신규 `scheduler_worker.py` 또는 CLI command

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
├── web/app.py
├── web/scheduler.py
├── server.py
└── scheduler_worker.py
```

    ### 데이터/제어 흐름
    1. 웹 서버는 요청 처리만 담당합니다.
2. 별도 scheduler worker가 cron 잡을 관리합니다.
3. scheduler 상태는 IPC/DB/파일/메모리 저장소를 통해 웹에서 조회합니다.

    ### API / CLI / 내부 계약 초안
    - `create_scheduler()`는 worker에서만 호출
- `scheduler status` 조회 인터페이스 정의

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - 웹 앱에서 scheduler 자동 시작을 옵션화합니다.
- 별도 scheduler entrypoint를 만듭니다.

    ### Phase 2 — 운영 가능한 형태로 보강
    - 배포 문서와 프로세스 관리(pm2/systemd/docker compose) 예시를 추가합니다.
- 중복 실행 방지 락을 도입합니다.

    ### Phase 3 — 고도화
    - 분산 락 또는 외부 job queue로 확장합니다.

    ## 9. 테스트 전략

    - 웹 앱 시작 시 scheduler 미기동 테스트
- 별도 worker에서 잡 등록 테스트
- 중복 실행 방지 테스트

    ## 10. 리스크와 대응

    - 로컬 개발자가 “왜 스케줄이 안 도냐” 혼동할 수 있습니다. → 개발 모드 옵션을 명확히 제공합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 웹과 scheduler 실행 책임이 분리된다.
- 중복 잡 실행 위험이 줄어든다.

    ## 12. 후속 확장 아이디어

    - 분산 잡 큐
- scheduler failover
