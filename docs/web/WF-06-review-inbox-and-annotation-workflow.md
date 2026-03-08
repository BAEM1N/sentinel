# WF-06 Review Inbox 및 Annotation Workflow

    - 영역: Web
    - 분류: 신규기능
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    저품질 trace, 경보 trace, 실패 평가 항목을 리뷰 대상 inbox로 모으고, 운영자/리뷰어가 주석을 남기고 후속 조치를 분류하는 기능입니다.

    ## 2. 왜 필요한가

    LLMOps 운영은 자동화만으로 끝나지 않습니다. 사람이 직접 보고 triage 하는 워크플로가 있어야 데이터셋 구축, prompt 개선, 버그 등록으로 연결됩니다.

    ## 3. 현재 코드 기준 진단

    - annotation API는 있지만 협업형 inbox UI가 없습니다.
- 어떤 trace를 먼저 봐야 하는지 우선순위 체계가 없습니다.

    ### 관련 코드/근거

    - `sentinel/tools/platform.py:80-126`
- `sentinel/tools/evaluation.py:58-113`

    ## 4. 목표 상태

    리뷰가 필요한 trace가 한곳에 모이고, 주석/상태/담당자/후속 액션이 함께 관리되는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - review inbox 목록
- annotation thread
- status/assignee/label
- 후속 action 연결

    ### 제외 범위
    - 범용 이슈 트래커 전체 대체

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - 리뷰 대상은 score 낮음, alert 발생, 수동 선택 등으로 생성될 수 있어야 합니다.
- 각 항목에 assignee, label, priority, status를 둘 수 있어야 합니다.
- annotation을 댓글 스레드처럼 볼 수 있어야 합니다.
- 후속 액션(프롬프트 개선, 데이터셋 편입, 버그 등록) 링크가 있어야 합니다.

    ### 비기능 요구사항
    - 목록은 필터와 정렬을 제공해야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - annotation backend
- 신규 review inbox 저장소/라우트/템플릿

    ### 권장 디렉터리/파일 구조
    ```text
templates/
├── review_inbox.html
└── review_item.html
```

    ### 데이터/제어 흐름
    1. 리뷰 대상이 자동 또는 수동으로 inbox에 추가됩니다.
2. 리뷰어가 항목을 열어 주석과 상태를 갱신합니다.
3. 필요 시 다른 기능(prompt/dataset/bug)으로 라우팅합니다.

    ### API / CLI / 내부 계약 초안
    - `ReviewItem`
- `POST /reviews/{id}/comment`
- `POST /reviews/{id}/assign`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - 리뷰 목록과 상세 뷰 구축
- annotation 표시/추가 기능 연결

    ### Phase 2 — 운영 가능한 형태로 보강
    - assignee/status/priority 추가
- 자동 inbox 생성 규칙 연결

    ### Phase 3 — 고도화
    - 외부 이슈 트래커(Jira/GitHub) 연계

    ## 9. 테스트 전략

    - annotation thread 렌더링 테스트
- status/assignee 업데이트 테스트
- 자동 inbox 생성 테스트

    ## 10. 리스크와 대응

    - 리뷰 워크플로가 복잡해질 수 있습니다. → 기본 상태 몇 개만 먼저 정의합니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 리뷰가 필요한 항목을 웹에서 관리할 수 있다.
- annotation과 후속 액션이 연결된다.

    ## 12. 후속 확장 아이디어

    - review SLA tracking
- quality council dashboard
