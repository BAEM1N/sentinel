# AG-01 프로바이더별 Fallback 모델 전략 정교화

    - 영역: Agent
    - 분류: 개선
    - 우선순위: 높음
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    Sentinel이 사용하는 primary model과 fallback model을 프로바이더별로 안전하게 해석하고, 잘못된 조합을 앱 시작 단계에서 차단하는 기능입니다. 현재는 fallback 이름이 사실상 OpenAI 계열 모델을 기준으로 작성되어 있어 Anthropic/Gemini/Ollama 계열로 provider를 바꿀 때 런타임에 뒤늦게 오류가 날 가능성이 있습니다.

    ## 2. 왜 필요한가

    운영 도구에서 모델 설정 오류는 기능 일부 실패가 아니라 전체 분석 플로우 중단으로 이어집니다. 특히 보고서 생성, LLM judge 평가, 프롬프트 개선 제안은 모두 모델 호출에 의존하므로 모델 해상도(resolution) 계층이 불안하면 제품 전체가 불안해집니다.

    ## 3. 현재 코드 기준 진단

    - fallback 기본값이 `gpt-5.3-instant`로 고정되어 있으며 provider별 기본값과 독립적으로 관리되지 않습니다.
- `_get_fallback_model()`은 현재 provider를 그대로 사용한 채 model 이름만 교체합니다.
- 설정이 잘못되어도 환경설정 로딩 단계가 아니라 실제 호출 직전 또는 객체 생성 중에 실패할 수 있습니다.
- 운영자가 현재 선택된 provider / primary / fallback 조합을 한눈에 확인할 수 있는 상태 요약 출력이 없습니다.

    ### 관련 코드/근거

    - `.env.example:8-20`
- `sentinel/agent.py:21-27`
- `sentinel/config.py:31-139`

    ## 4. 목표 상태

    provider별로 지원 모델군, 기본 primary, 기본 fallback, 허용되지 않는 fallback 조합이 명시적으로 선언되고, 앱 시작 시점에 유효성 검사를 통과한 경우에만 agent가 생성되는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - provider별 fallback 기본값 선언
- 모델 조합 검증 함수 도입
- 구성 스냅샷 출력(운영자 확인용)
- README / `.env.example` 동기화

    ### 제외 범위
    - 실제 모델 성능 벤치마크
- 모델 비용 자동 최적화 로직

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - provider가 `openai/anthropic/gemini/ollama/...` 중 무엇인지에 따라 fallback 기본값이 달라져야 합니다.
- 운영자가 `SENTINEL_FALLBACK_MODEL`을 직접 넣었을 때 provider와 호환되지 않으면 명시적 예외를 발생시켜야 합니다.
- primary/fallback/base_url/api_key 해상 결과를 구조화된 설정 객체로 반환해야 합니다.
- CLI와 웹 서버 시작 시 동일한 설정 검증 경로를 사용해야 합니다.

    ### 비기능 요구사항
    - 검증 실패 메시지는 운영자가 바로 수정할 수 있도록 구체적이어야 합니다.
- 새 provider 추가 시 `_PROVIDER_DEFAULTS` 외 한두 곳만 수정하면 되도록 응집도를 높여야 합니다.
- 테스트에서 provider 조합을 빠르게 검증할 수 있도록 pure function 중심으로 설계해야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - `sentinel/config.py` — 설정 해상도 로직 재구성
- `sentinel/agent.py` — fallback 생성 방식을 provider-aware 하게 수정
- `main.py`, `server.py` — 시작 시 설정 요약 출력 지점
- 신규 `sentinel/settings.py` 또는 `sentinel/core/model_config.py` — 설정 스키마/검증 모듈

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
├── core/
│   └── model_config.py      # provider/model/fallback 해상도
├── config.py                # env 로딩 + 모델 팩토리 연결
└── agent.py                 # create_sentinel_agent()
```

    ### 데이터/제어 흐름
    1. 환경변수를 읽어 raw 설정을 수집합니다.
2. provider별 기본값 테이블에서 primary/fallback 후보를 정합니다.
3. 사용자 override가 있으면 호환성 검사를 수행합니다.
4. 검증 통과 시 settings 객체를 만들고 ChatModel 인스턴스를 생성합니다.
5. 시작 로그에 provider, primary, fallback, base_url 유무를 출력합니다.

    ### API / CLI / 내부 계약 초안
    - `resolve_model_settings(env) -> ModelSettings`
- `validate_model_settings(settings) -> None`
- `create_chat_model(settings, role="primary"|"fallback")`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - 현재 `_PROVIDER_DEFAULTS`를 기반으로 provider별 fallback 기본값 테이블을 추가합니다.
- 설정 해상도 함수를 pure function으로 추출합니다.
- 잘못된 조합에 대해 사람이 읽을 수 있는 예외 메시지를 정의합니다.

    ### Phase 2 — 운영 가능한 형태로 보강
    - CLI/웹 시작 경로에서 설정 스냅샷을 로그로 남깁니다.
- README와 `.env.example`에 provider별 fallback 예시를 추가합니다.
- fallback 미설정 시 자동 선택 규칙을 문서화합니다.

    ### Phase 3 — 고도화
    - 모델 가용성 ping 또는 dry-run 검증을 옵션으로 제공합니다.
- 운영자용 `/health` 또는 CLI `--show-config`와 연결합니다.

    ## 9. 테스트 전략

    - provider별 기본 fallback 해상 테스트
- 호환되지 않는 fallback 모델명 입력 시 예외 테스트
- lmstudio/openrouter 등 OpenAI-compatible provider 조합 테스트
- 웹/CLI 시작 경로가 동일한 설정 해상 함수를 쓰는지 통합 테스트

    ## 10. 리스크와 대응

    - 실제 모델명과 공급자 정책이 자주 바뀔 수 있으므로 완전한 whitelist는 유지비가 큽니다. → 최소한 provider별 기본값과 명백한 오입력 차단에 집중합니다.
- local provider는 모델명 검증이 느슨해야 할 수 있습니다. → strict/lenient 모드를 분리합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - provider별 fallback 기본값이 문서화되고 코드에 반영되어 있다.
- 잘못된 조합은 앱 시작 시 바로 실패한다.
- 운영자가 현재 primary/fallback 조합을 로그에서 즉시 확인할 수 있다.

    ## 12. 후속 확장 아이디어

    - 모델별 비용/품질 점수 기반 자동 fallback 추천
- provider 장애 시 cross-provider fallback 전략
