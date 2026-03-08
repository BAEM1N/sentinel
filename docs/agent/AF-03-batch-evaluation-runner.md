# AF-03 Batch Evaluation Runner

    - 영역: Agent
    - 분류: 신규기능
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    데이터셋 또는 필터링된 trace 집합을 대상으로 LLM judge 평가를 배치로 수행하고, 결과를 score와 summary report로 남기는 백엔드 기능입니다. 이는 향후 Evaluation Dashboard의 핵심 실행 엔진이 됩니다.

    ## 2. 왜 필요한가

    개별 trace를 하나씩 평가하는 것으로는 회귀 검증이나 릴리스 비교를 운영 수준에서 수행하기 어렵습니다. 일괄 평가 실행기(batch runner)가 있어야 품질 운영이 체계화됩니다.

    ## 3. 현재 코드 기준 진단

    - `evaluate_with_llm`는 단일 trace 중심입니다.
- dataset은 있지만 batch evaluation orchestrator가 없습니다.
- 품질 비교나 릴리스 회귀 확인을 위해 반복 수작업이 필요합니다.

    ### 관련 코드/근거

    - `sentinel/tools/evaluation.py:58-113`
- `sentinel/tools/platform.py:10-77`
- `skills/langfuse-ops/SKILL.md:219-237,332-357`

    ## 4. 목표 상태

    운영자가 dataset 또는 쿼리 결과를 배치 평가로 돌리고, run 단위 결과/점수 요약/실패 항목 목록을 받을 수 있는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - batch job 정의
- 대상 집합 수집
- 평가 병렬 실행
- 결과 집계

    ### 제외 범위
    - 완전한 평가 UI

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - 대상은 dataset, trace query, session 집합 중 하나로 지정할 수 있어야 합니다.
- 평가 기준(criteria), 동시성, 재시도, 샘플링 정책을 설정할 수 있어야 합니다.
- 결과는 score 저장과 별개로 evaluation run record를 남겨야 합니다.
- 실패 항목만 재실행할 수 있어야 합니다.

    ### 비기능 요구사항
    - 대량 평가 시 비용 한도를 제어할 수 있어야 합니다.
- 병렬화하더라도 provider rate limit을 넘기지 않도록 해야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - 신규 `sentinel/eval_runner/`
- `sentinel/tools/evaluation.py`
- `sentinel/tools/platform.py`
- 향후 background job system과 연계

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
├── eval_runner/
│   ├── models.py
│   ├── runner.py
│   ├── collectors.py
│   └── aggregators.py
└── tools/evaluation.py
```

    ### 데이터/제어 흐름
    1. 평가 대상 집합을 수집합니다.
2. 배치 실행 단위를 생성합니다.
3. rate limit과 concurrency를 고려해 평가를 수행합니다.
4. score를 저장하고 run summary를 계산합니다.
5. 실패/저점수 항목을 별도로 출력합니다.

    ### API / CLI / 내부 계약 초안
    - `EvaluationRunRequest`
- `EvaluationRunResult`
- `rerun_failed_items(run_id)`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - dataset 기반 batch runner를 구현합니다.
- run summary와 failed item 목록을 생성합니다.

    ### Phase 2 — 운영 가능한 형태로 보강
    - trace query 기반 대상 수집을 지원합니다.
- 비용 한도와 concurrency 제어를 추가합니다.

    ### Phase 3 — 고도화
    - 웹 대시보드와 연결합니다.
- prompt version 비교 모드, release 비교 모드를 추가합니다.

    ## 9. 테스트 전략

    - dataset batch collection 테스트
- 실패 항목 재실행 테스트
- 요약 집계 정확성 테스트

    ## 10. 리스크와 대응

    - 배치 평가 비용이 빠르게 커질 수 있습니다. → 샘플링, 예산 상한, dry-run estimate 기능을 넣습니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 단일 trace가 아닌 집합 평가가 가능하다.
- 평가 결과가 run 단위로 추적된다.
- 실패 항목 재실행이 가능하다.

    ## 12. 후속 확장 아이디어

    - 평가 결과 자동 회귀 차단
- evaluation campaign UI
