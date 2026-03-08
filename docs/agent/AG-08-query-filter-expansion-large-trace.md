# AG-08 조회 필터 확장과 대용량 Trace 처리

    - 영역: Agent
    - 분류: 개선
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    Langfuse SDK가 이미 제공하는 environment/release/version/order_by/page 등 더 풍부한 조회 축을 Sentinel tool에 노출하고, 큰 trace payload는 요약/헤드/테일 중심으로 안정적으로 다루도록 개선하는 문서입니다.

    ## 2. 왜 필요한가

    운영자는 단순히 최근 20개 trace만 보는 것이 아니라 특정 release, 특정 environment, 특정 prompt version에서 무슨 일이 일어나는지를 알고 싶어합니다. 또한 큰 payload를 단순 잘라내면 중요한 후반부 오류 신호가 사라질 수 있습니다.

    ## 3. 현재 코드 기준 진단

    - `list_traces` 필터가 name/user/session/date/tags 정도로 제한적입니다.
- `query_metrics`도 필터가 제한적입니다.
- `get_trace_detail`, `evaluate_with_llm`는 긴 입력/출력을 단순 truncate 합니다.

    ### 관련 코드/근거

    - `skills/langfuse-ops/SKILL.md:53-67`
- `skills/langfuse-ops/SKILL.md:174-217`
- `sentinel/tools/traces.py:11-19,81-82`
- `sentinel/tools/metrics.py:24-33`
- `sentinel/tools/evaluation.py:69-71`

    ## 4. 목표 상태

    운영자가 release/environment/version/model 기준으로 좁혀서 조회할 수 있고, 긴 trace도 핵심 정보가 보존된 형태로 분석 가능한 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - trace/metrics 필터 확장
- pagination/order_by 지원
- head/tail/summary 기반 긴 텍스트 처리
- 운영자용 기본 쿼리 프리셋

    ### 제외 범위
    - Langfuse 전체 검색엔진 대체
- 대규모 인덱싱 시스템 구현

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - list_traces에 environment/release/version/page/order_by/limit가 추가되어야 합니다.
- query_metrics는 더 다양한 filter set을 받도록 일반화되어야 합니다.
- 긴 trace는 head/tail/section summary 구조를 반환해야 합니다.
- 기본 프리셋(최근 배포 영향, production error, 비용 급증 user 등)을 지원해야 합니다.

    ### 비기능 요구사항
    - 기본값은 현재 UX를 크게 깨지 않아야 합니다.
- 긴 trace 처리 전략은 토큰 비용을 폭증시키지 않아야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - `sentinel/tools/traces.py`
- `sentinel/tools/metrics.py`
- 신규 `sentinel/core/query_presets.py`
- 신규 `sentinel/core/text_windows.py`

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
├── core/
│   ├── query_presets.py
│   └── text_windows.py
└── tools/
```

    ### 데이터/제어 흐름
    1. 운영자가 richer filter를 입력합니다.
2. tool이 Langfuse SDK 쿼리로 매핑합니다.
3. 응답 payload가 큰 경우 windowing helper로 요약/분할합니다.
4. 에이전트는 summary를 먼저 보고 필요 시 detail을 재조회합니다.

    ### API / CLI / 내부 계약 초안
    - `TraceQuery` object
- `MetricsQuery` object
- `window_text(text, strategy="head-tail")`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - filter 인자를 확장합니다.
- 긴 텍스트 head/tail helper를 도입합니다.
- 기본 프리셋 2~3개를 문서화합니다.

    ### Phase 2 — 운영 가능한 형태로 보강
    - pagination meta와 order_by를 응답에 포함합니다.
- metrics filter를 generic dict 기반으로 확장합니다.

    ### Phase 3 — 고도화
    - semantic summary 또는 anomaly extraction을 도입합니다.
- web Trace Explorer와 같은 query model을 공유합니다.

    ## 9. 테스트 전략

    - 새 필터가 Langfuse SDK 파라미터로 올바르게 매핑되는지 테스트
- 긴 payload windowing 테스트
- 프리셋 query regression 테스트

    ## 10. 리스크와 대응

    - 필터가 많아지면 UX가 복잡해질 수 있습니다. → preset + advanced mode를 분리합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 운영에서 필요한 주요 필터 축이 도구에 반영된다.
- 큰 trace가 단순 truncate보다 정보 보존도가 높은 방식으로 처리된다.

    ## 12. 후속 확장 아이디어

    - release comparison 보고서
- anomaly-first trace viewer
