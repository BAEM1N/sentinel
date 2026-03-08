# WF-03 Evaluation Campaign Dashboard

    - 영역: Web
    - 분류: 신규기능
    - 우선순위: 높음
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    dataset 또는 trace 집합을 대상으로 batch evaluation을 실행하고, 결과를 run 단위로 시각화하는 대시보드입니다. 품질 회귀를 보는 핵심 운영 화면입니다.

    ## 2. 왜 필요한가

    LLM 시스템은 바뀔 때마다 품질이 변합니다. 단발성 점수 조회가 아니라 “이번 릴리스가 지난주보다 나빠졌는지”를 보여주는 화면이 필요합니다.

    ## 3. 현재 코드 기준 진단

    - 개별 score 조회/생성 도구는 있지만 campaign 개념이 없습니다.
- batch evaluation runner가 구현되어 있지 않습니다.

    ### 관련 코드/근거

    - `sentinel/tools/evaluation.py:11-113`
- `sentinel/tools/platform.py:10-77`
- `skills/langfuse-ops/SKILL.md:332-357`

    ## 4. 목표 상태

    운영자가 evaluation run을 생성하고, 평균 점수/저점수 항목/버전 비교를 한 화면에서 보는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - campaign 생성 UI
- run summary
- failed/low-score items list
- version/release comparison

    ### 제외 범위
    - 실시간 온라인 평가 전부

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - dataset 기반 또는 trace query 기반 평가 run 생성
- 평가 기준과 샘플 수 설정
- 평균/중앙값/분포/최저점 항목 표시
- 관련 prompt/model/release와 연결

    ### 비기능 요구사항
    - 대량 평가 결과를 페이지네이션 또는 lazy load 해야 합니다.
- 비용 추정과 실제 비용을 보여줄 수 있어야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - batch evaluation runner(backend)
- 신규 템플릿/라우트

    ### 권장 디렉터리/파일 구조
    ```text
templates/
├── eval_campaign_list.html
├── eval_campaign_new.html
└── eval_campaign_detail.html
```

    ### 데이터/제어 흐름
    1. 사용자가 campaign을 생성합니다.
2. backend runner가 배치 평가를 수행합니다.
3. 결과를 집계해 dashboard에서 시각화합니다.
4. 저점수 항목은 review inbox나 dataset builder로 연결합니다.

    ### API / CLI / 내부 계약 초안
    - `POST /eval-campaigns`
- `GET /eval-campaigns`
- `GET /eval-campaigns/{run_id}`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - run list/detail 화면 구축
- 평균/최저점/실패 목록 표시

    ### Phase 2 — 운영 가능한 형태로 보강
    - 비교 뷰(release/prompt version) 추가
- 비용 추정/실제 비용 표시

    ### Phase 3 — 고도화
    - 회귀 차단 정책과 연결

    ## 9. 테스트 전략

    - campaign 상태 전이 테스트
- 집계 값 정확성 테스트
- comparison view 테스트

    ## 10. 리스크와 대응

    - 평가 비용이 커질 수 있습니다. → 예산 상한, sample mode 제공.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 배치 평가 결과를 웹에서 볼 수 있다.
- 버전/릴리스 회귀를 시각적으로 확인할 수 있다.

    ## 12. 후속 확장 아이디어

    - auto gate for deployment
