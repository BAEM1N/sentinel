# AG-06 영속 Checkpoint와 작업공간 분리

    - 영역: Agent
    - 분류: 개선
    - 우선순위: 높음
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    대화 상태와 작업공간을 메모리/상대경로에서 분리해, 재시작 후에도 지속 가능한 agent 상태 관리와 명확한 artifact 경로 체계를 만드는 개선입니다.

    ## 2. 왜 필요한가

    운영형 agent는 “어제 하던 분석을 오늘 이어서 볼 수 있느냐”가 매우 중요합니다. 현재는 프로세스 재시작 시 체크포인트가 사라지고, 보고서 저장 위치도 실행 위치에 따라 달라질 수 있습니다.

    ## 3. 현재 코드 기준 진단

    - `InMemorySaver()`를 사용합니다.
- `REPORTS_DIR`와 agent backend root가 기능적으로 가까이 묶여 있습니다.
- 환경변수 기본값이 상대경로(`./reports`, `./skills/`)라 실행 위치에 민감합니다.

    ### 관련 코드/근거

    - `sentinel/agent.py:19-20,38-40`
- `.env.example:29-31`
- `sentinel/web/routes.py:12`
- `sentinel/web/app.py:43-44`

    ## 4. 목표 상태

    checkpoint 저장소, working workspace, published reports directory가 서로 분리되고, 재시작 이후에도 세션 컨텍스트가 이어질 수 있는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - checkpoint backend 교체
- workspace/artifact 경로 분리
- 절대경로/앱루트 기준 경로 정책
- 복구 가능한 세션 식별자 설계

    ### 제외 범위
    - 분산 작업 스토리지 전체 설계
- S3/GCS 아카이브까지의 완전한 구현

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - 세션 state가 프로세스 재시작 후 복구 가능해야 합니다.
- 보고서 저장 경로와 agent 작업공간이 별도여야 합니다.
- CLI와 웹이 같은 path resolver를 사용해야 합니다.
- 운영자가 현재 storage 위치를 확인할 수 있어야 합니다.

    ### 비기능 요구사항
    - 작은 규모에서는 SQLite로 시작 가능해야 합니다.
- 경로 정책은 OS와 실행 위치에 독립적이어야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - `sentinel/agent.py`
- 신규 `sentinel/core/paths.py`
- 신규 `sentinel/core/checkpoints.py`
- `main.py`, `server.py`, `sentinel/web/*` 경로 참조부

    ### 권장 디렉터리/파일 구조
    ```text
sentinel-data/
├── checkpoints/
├── workspace/
└── reports/
```

    ### 데이터/제어 흐름
    1. 앱 시작 시 path resolver가 data root를 계산합니다.
2. checkpoint backend가 세션 저장소를 초기화합니다.
3. agent는 workspace를 통해 작업 파일을 다루고, reports는 publish artifact로만 사용합니다.
4. 세션 재개 시 thread_id/session_id로 이전 checkpoint를 복구합니다.

    ### API / CLI / 내부 계약 초안
    - `PathSettings(data_root, checkpoint_dir, workspace_dir, reports_dir)`
- `create_checkpointer(settings)`
- `resume_session(thread_id)`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - 경로 해상도 모듈을 도입합니다.
- checkpoint 저장소를 SQLite 기반으로 교체합니다.
- reports/workspace/checkpoints 디렉터리를 분리합니다.

    ### Phase 2 — 운영 가능한 형태로 보강
    - 세션 재개 명령이나 옵션을 CLI에 추가합니다.
- 웹에서도 최근 세션 조회를 지원할 수 있는 기반을 마련합니다.

    ### Phase 3 — 고도화
    - Postgres나 외부 스토리지로 확장합니다.
- 세션 TTL 및 보존정책을 도입합니다.

    ## 9. 테스트 전략

    - 프로세스 재시작 후 checkpoint 복구 테스트
- 경로 해상도가 실행 위치와 무관한지 테스트
- reports/workspace/checkpoints 분리 테스트

    ## 10. 리스크와 대응

    - 기존 상대경로 사용자와 호환성 이슈가 생길 수 있습니다. → migration guide와 default fallback을 제공합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - checkpoint가 메모리가 아닌 영속 저장소를 사용한다.
- workspace와 published reports가 분리된다.
- CLI/웹이 동일한 경로 정책을 쓴다.

    ## 12. 후속 확장 아이디어

    - 작업 이력 UI
- 세션 북마크 기능
