# AG-02 외부 API 호출 복원력 계층

    - 영역: Agent
    - 분류: 개선
    - 우선순위: 높음
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    Langfuse API, LLM 모델 호출, 향후 외부 시스템 호출에 공통으로 적용할 timeout / retry / 예외 정규화 / 로깅 계층을 추가하는 개선입니다. 지금은 도구마다 직접 API를 호출해 실패 방식이 제각각입니다.

    ## 2. 왜 필요한가

    Sentinel은 본질적으로 외부 서비스 위에서 동작합니다. 외부 서비스가 느리거나 일시적으로 실패하는 것은 정상 시나리오에 가깝기 때문에, 실패를 “예외 상황”이 아니라 “설계 대상”으로 다뤄야 합니다.

    ## 3. 현재 코드 기준 진단

    - 대부분의 tool 함수가 외부 API를 직접 호출합니다.
- 일부만 `try/except`를 가지고 있고, 예외 유형이 통일되어 있지 않습니다.
- 시간 초과, 재시도, 백오프, 에러 코드 분류가 없습니다.
- 실패 시 운영자에게 보여줄 메시지와 디버그용 상세 정보가 분리되어 있지 않습니다.

    ### 관련 코드/근거

    - `sentinel/tools/traces.py:31-106`
- `sentinel/tools/evaluation.py:69-113`
- `sentinel/tools/metrics.py:82-83,333-388,397-474`
- `sentinel/web/notify.py:22-140`

    ## 4. 목표 상태

    모든 외부 호출이 공통 wrapper를 통해 실행되고, 재시도 가능한 오류와 즉시 실패해야 하는 오류가 분리되며, 사용자 메시지/운영 로그/메트릭이 일관되게 남는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - Langfuse 호출 wrapper
- LLM invoke wrapper
- 알림 채널 wrapper
- 에러 taxonomy와 로그 컨텍스트 설계

    ### 제외 범위
    - 완전한 circuit breaker 인프라
- 분산 tracing 시스템 도입 자체

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - timeout 값을 환경변수나 설정 객체로 관리할 수 있어야 합니다.
- 재시도 가능한 오류(5xx, timeout, connection reset)와 재시도 불가능 오류(4xx, validation) 분리가 필요합니다.
- tool 함수는 실패를 문자열로 얼버무리지 말고 구조화된 실패 결과를 반환할 수 있어야 합니다.
- 알림 전송도 채널별 실패 사유를 표준 포맷으로 모아야 합니다.

    ### 비기능 요구사항
    - 재시도는 멱등성을 해치지 않는 범위에서만 수행해야 합니다.
- 로그에는 trace_id / tool_name / provider / retry_count 같은 컨텍스트가 남아야 합니다.
- 호출 wrapper는 테스트에서 쉽게 mocking 가능해야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - 신규 `sentinel/core/resilience.py` — retry, timeout, error mapping
- 신규 `sentinel/core/errors.py` — 도메인 예외 정의
- `sentinel/tools/*.py` — 직접 호출 지점을 wrapper 경유로 변경
- `sentinel/web/notify.py` — 채널 결과 구조화

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
├── core/
│   ├── resilience.py
│   ├── errors.py
│   └── logging.py
├── tools/
└── web/
    └── notify.py
```

    ### 데이터/제어 흐름
    1. tool 또는 notify 함수가 외부 API 호출을 요청합니다.
2. wrapper가 timeout, retry policy, log context를 부여합니다.
3. 호출 결과를 성공/재시도실패/영구실패로 분류합니다.
4. 운영자용 메시지와 디버그 메타데이터를 함께 반환합니다.
5. 상위 계층은 이 구조를 이용해 UI/CLI/로그에 다르게 표시합니다.

    ### API / CLI / 내부 계약 초안
    - `call_with_resilience(name, fn, retry_policy, timeout, context)`
- `SentinelExternalError(code, retryable, user_message, debug_context)`
- `NotificationResult(channel, success, error_code, detail)`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - Langfuse/LLM 호출 wrapper를 먼저 도입합니다.
- 도메인 예외 타입 3~5개를 정의합니다(Timeout, UpstreamUnavailable, InvalidRequest 등).
- 기존 tool 함수에서 직접 예외를 던지던 지점을 wrapper 호출로 교체합니다.

    ### Phase 2 — 운영 가능한 형태로 보강
    - notify 채널에도 동일한 결과 구조를 적용합니다.
- 실패 통계를 로그 또는 메트릭으로 노출합니다.
- 재시도 정책을 환경변수 기반 설정으로 외부화합니다.

    ### Phase 3 — 고도화
    - circuit breaker 또는 provider failover 정책을 도입합니다.
- 실패 원인 top-N 리포트를 자동 생성합니다.

    ## 9. 테스트 전략

    - timeout 발생 시 재시도 횟수 테스트
- 4xx 오류는 재시도하지 않는지 테스트
- tool 함수가 구조화된 오류를 반환하는지 테스트
- 알림 채널 일부 실패 시 전체 결과 집계 테스트

    ## 10. 리스크와 대응

    - 모든 호출을 래핑하면 코드가 장황해질 수 있습니다. → 공통 decorator/helper로 줄입니다.
- 재시도는 비용을 키울 수 있습니다. → LLM 호출에는 횟수와 대상 에러를 보수적으로 제한합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 외부 호출이 공통 wrapper를 통해 실행된다.
- 실패 결과가 구조화되어 상위 계층에서 재사용 가능하다.
- 운영자가 “왜 실패했는지”를 로그와 사용자 메시지에서 모두 파악할 수 있다.

    ## 12. 후속 확장 아이디어

    - Prometheus 메트릭 연동
- provider별 SLA/에러율 기반 라우팅
