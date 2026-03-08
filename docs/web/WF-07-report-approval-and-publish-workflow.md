# WF-07 보고서 승인 및 발행 Workflow

    - 영역: Web
    - 분류: 신규기능
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    보고서를 생성 즉시 배포하지 않고, Draft → Review → Approved → Published 단계로 관리하는 기능입니다.

    ## 2. 왜 필요한가

    LLM 생성 보고서는 항상 검토가 필요할 수 있습니다. 특히 외부 고객/경영진 보고용일수록 승인 단계를 거치지 않은 자동 발송은 위험합니다.

    ## 3. 현재 코드 기준 진단

    - 생성 즉시 저장 및 알림 전송 구조입니다.
- draft/review/publish 개념이 없습니다.

    ### 관련 코드/근거

    - `sentinel/web/routes.py:170-175`
- `sentinel/web/scheduler.py:63-65`
- `sentinel/web/notify.py:131-140`

    ## 4. 목표 상태

    보고서가 승인 상태를 가진 artifact가 되고, 승인된 경우에만 외부 채널로 발행되는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - report state machine
- draft/review/publish UI
- 알림 전송 시점 제어
- approval 기록

    ### 제외 범위
    - 복잡한 문서 협업 에디터

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - 보고서 상태는 draft/review/approved/published/rejected를 가져야 합니다.
- 승인 전 자동 알림 발송을 막을 수 있어야 합니다.
- 승인자는 코멘트를 남길 수 있어야 합니다.
- 월간 보고서 등 특정 종류는 승인 필수 정책을 가질 수 있어야 합니다.

    ### 비기능 요구사항
    - 현재 즉시 발송 플로우를 필요 시 유지할 수 있도록 정책화해야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - ReportService
- approval backend
- 신규 report workflow UI

    ### 권장 디렉터리/파일 구조
    ```text
templates/
├── reports.html
├── report_review.html
└── report_publish_history.html
```

    ### 데이터/제어 흐름
    1. 보고서 생성 시 draft 상태로 저장합니다.
2. 리뷰어가 내용을 확인하고 승인/거절합니다.
3. approved 상태에서만 publish job이 실행됩니다.
4. 발행 이력과 채널 결과가 기록됩니다.

    ### API / CLI / 내부 계약 초안
    - `ReportState`
- `POST /reports/{id}/submit-review`
- `POST /reports/{id}/approve`
- `POST /reports/{id}/publish`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - draft/review 상태 도입
- 승인 전 발송 막기

    ### Phase 2 — 운영 가능한 형태로 보강
    - 승인자 코멘트와 publish history 추가
- 보고서 종류별 정책 지원

    ### Phase 3 — 고도화
    - 다중 승인, SLA, escalation 도입

    ## 9. 테스트 전략

    - 승인 전 publish 차단 테스트
- 상태 전이 테스트
- 알림 발송 시점 테스트

    ## 10. 리스크와 대응

    - 보고서 배포 속도가 늦어질 수 있습니다. → 일간 내부 보고서는 auto-publish 정책 허용.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 보고서가 승인 가능한 artifact가 된다.
- 발송 시점이 통제된다.

    ## 12. 후속 확장 아이디어

    - 전자결재 연동
