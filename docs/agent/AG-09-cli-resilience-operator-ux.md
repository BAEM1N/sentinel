# AG-09 CLI 복원력 및 운영자 UX 고도화

    - 영역: Agent
    - 분류: 개선
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    운영자가 가장 빨리 사용할 수 있는 CLI 인터페이스에 예외 복원력, 구조화 출력, 세션 재개, dry-run, 파일 저장 같은 실무 기능을 추가하는 개선입니다.

    ## 2. 왜 필요한가

    현재 CLI는 “작동하면 편한 데모”에 가깝고, 실패나 재시작, 자동화, 파이프라인 연계 같은 실제 운영 시나리오에는 다소 약합니다.

    ## 3. 현재 코드 기준 진단

    - `interactive()` 루프에서 개별 질의 실패를 별도로 처리하지 않습니다.
- `--query` 외 옵션이 거의 없습니다.
- 결과는 텍스트 출력 위주라 shell automation과 연계가 어렵습니다.
- thread_id/session resume 기능이 없습니다.

    ### 관련 코드/근거

    - `main.py:22-80`

    ## 4. 목표 상태

    운영자가 CLI만으로도 안전하게 질의를 반복하고, JSON 출력과 파일 저장을 통해 자동화 스크립트에 연결할 수 있는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - 예외 처리 강화
- JSON/text 출력 모드
- thread/session 옵션
- dry-run / config 확인 기능

    ### 제외 범위
    - 완전한 TUI 구축
- 모든 운영 콘솔 기능을 CLI에 다 넣기

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - `--json`, `--output`, `--thread-id`, `--resume`, `--dry-run`, `--show-config` 옵션이 필요합니다.
- interactive mode에서 한 번 실패해도 프로세스가 종료되지 않아야 합니다.
- 에러 출력은 사람이 읽을 수 있어야 하고, 필요하면 JSON으로도 나갈 수 있어야 합니다.
- 향후 batch job이 CLI를 래핑해 사용해도 안정적으로 동작해야 합니다.

    ### 비기능 요구사항
    - 표준 출력/표준 오류 분리가 가능해야 합니다.
- 기존 사용법과의 호환성이 유지되어야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - `main.py`
- `sentinel/agent.py`
- 신규 `sentinel/cli/formatter.py`

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
├── cli/
│   └── formatter.py
└── main.py
```

    ### 데이터/제어 흐름
    1. CLI 인자를 파싱합니다.
2. 실행 모드(query / interactive / dry-run / show-config)를 분기합니다.
3. agent 호출 결과를 formatter가 text/json으로 직렬화합니다.
4. interactive mode에서는 개별 질의 실패를 잡고 다음 질의를 계속 받습니다.

    ### API / CLI / 내부 계약 초안
    - `format_result(result, mode="text"|"json")`
- `run_query(..., output_mode, dry_run=False)`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - interactive 예외 처리 추가
- `--json`, `--output`, `--show-config` 지원
- stderr/exit code 정리

    ### Phase 2 — 운영 가능한 형태로 보강
    - `--thread-id`, `--resume`, `--dry-run` 추가
- JSON envelope 표준화

    ### Phase 3 — 고도화
    - batch query 파일 입력, 템플릿 query, 최근 실행 재시도 기능 추가
- Rich/Typer 기반 개선을 검토

    ## 9. 테스트 전략

    - CLI 옵션 파싱 테스트
- interactive 모드 예외 복원 테스트
- JSON 출력 스냅샷 테스트

    ## 10. 리스크와 대응

    - 옵션이 늘어나면 진입 장벽이 높아질 수 있습니다. → 기본 사용법은 그대로 두고 advanced 옵션을 분리합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 실패가 CLI 전체 종료로 이어지지 않는다.
- 자동화 가능한 JSON 출력이 가능하다.
- 운영자가 설정 상태와 세션을 제어할 수 있다.

    ## 12. 후속 확장 아이디어

    - TUI dashboard
- shell completion
