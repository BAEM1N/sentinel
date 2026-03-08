# WF-05 Trace 기반 Dataset Builder

    - 영역: Web
    - 분류: 신규기능
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    문제가 있거나 대표성이 있는 trace를 평가 데이터셋으로 편입하고, expected output을 붙여 regression test 자산으로 만드는 기능입니다.

    ## 2. 왜 필요한가

    좋은 평가 체계는 좋은 데이터셋에서 시작됩니다. 운영 중 발견된 실제 trace를 곧바로 평가셋으로 연결할 수 있어야 품질 개선 루프가 닫힙니다.

    ## 3. 현재 코드 기준 진단

    - dataset API는 있으나 UI가 없습니다.
- trace → dataset 전환 흐름이 수작업입니다.

    ### 관련 코드/근거

    - `sentinel/tools/platform.py:10-77`
- `sentinel/tools/traces.py:68-106`

    ## 4. 목표 상태

    운영자가 trace detail 화면에서 바로 dataset item을 만들고, expected output과 태그를 붙여 저장할 수 있는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - dataset list/create UI
- trace to dataset action
- expected output 편집
- golden/candidate tagging

    ### 제외 범위
    - 완전한 데이터 라벨링 플랫폼

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - trace detail에서 “Add to Dataset” 액션이 가능해야 합니다.
- 입력은 trace에서 가져오고 expected output을 편집할 수 있어야 합니다.
- dataset item에 태그와 source_trace_id를 남겨야 합니다.

    ### 비기능 요구사항
    - 한 번에 다수 trace를 선택해 편입하는 batch UX가 있으면 좋습니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - `sentinel/tools/platform.py`
- Trace Explorer와 연동되는 웹 라우트/템플릿

    ### 권장 디렉터리/파일 구조
    ```text
templates/
├── datasets.html
├── dataset_detail.html
└── dataset_item_form.html
```

    ### 데이터/제어 흐름
    1. 운영자가 trace를 선택합니다.
2. dataset item 생성 폼이 열립니다.
3. 입력/출처 trace가 자동 채워집니다.
4. expected output과 태그를 넣고 저장합니다.

    ### API / CLI / 내부 계약 초안
    - `POST /datasets`
- `POST /datasets/{name}/items`
- `POST /traces/{trace_id}/to-dataset`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - dataset 목록/상세 화면
- trace->dataset 단건 편입

    ### Phase 2 — 운영 가능한 형태로 보강
    - batch add, tag, bulk edit
- evaluation campaign과 연결

    ### Phase 3 — 고도화
    - versioned datasets
- approval for golden set changes

    ## 9. 테스트 전략

    - trace source preservation 테스트
- expected output 저장 테스트
- batch add 테스트

    ## 10. 리스크와 대응

    - trace에 민감정보가 포함될 수 있습니다. → redaction/approval 옵션 필요.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 운영 데이터가 빠르게 평가셋으로 전환된다.
- source trace provenance가 유지된다.

    ## 12. 후속 확장 아이디어

    - dataset diff
- golden set review
