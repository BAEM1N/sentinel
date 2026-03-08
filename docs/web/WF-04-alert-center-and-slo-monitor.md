# WF-04 Alert Center 및 SLO 모니터

    - 영역: Web
    - 분류: 신규기능
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    비용 급증, 레이턴시 증가, 품질 점수 하락, 에러율 상승 같은 운영 이벤트를 룰 기반으로 감지하고 알리는 화면과 엔진입니다.

    ## 2. 왜 필요한가

    보고서는 사후 분석에 강하지만, 운영은 사전 경보가 중요합니다. Alert Center가 있어야 Sentinel이 리포트 생성기에서 운영 관제 도구로 확장됩니다.

    ## 3. 현재 코드 기준 진단

    - 알림 채널은 있지만 경보 규칙 엔진이 없습니다.
- 정기 보고서는 있지만 threshold 기반 실시간 경보가 없습니다.

    ### 관련 코드/근거

    - `sentinel/tools/metrics.py:23-83`
- `sentinel/web/notify.py:22-140`

    ## 4. 목표 상태

    운영자가 경보 규칙을 정의하고, 활성 경보와 최근 경보 이력을 한곳에서 확인할 수 있는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - alert rule 정의
- evaluation/metrics 기반 경보 생성
- 활성 alert 목록
- acknowledge/resolve 흐름

    ### 제외 범위
    - 완전한 NOC 시스템

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - 비용, latency, error rate, score drop 등의 조건 룰 지원
- 알림 채널 매핑
- ack/resolved 상태 관리
- 관련 trace/report/evaluation 링크 제공

    ### 비기능 요구사항
    - 과도한 alert noise를 막기 위한 debounce/suppression가 필요합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - 신규 `alerts/` backend
- 신규 web templates/routes
- notify 모듈 연계

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
├── alerts/
│   ├── rules.py
│   ├── engine.py
│   └── store.py
└── templates/
    ├── alerts.html
    └── alert_detail.html
```

    ### 데이터/제어 흐름
    1. metrics/eval 결과를 주기적으로 평가합니다.
2. rule engine이 임계치 초과를 감지합니다.
3. alert를 생성하고 채널로 전송합니다.
4. 웹에서 alert 상태를 triage 합니다.

    ### API / CLI / 내부 계약 초안
    - `AlertRule`
- `AlertEvent`
- `POST /alerts/rules`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - 정적 룰 몇 개와 alert list 화면 구현
- Slack/Telegram 연계

    ### Phase 2 — 운영 가능한 형태로 보강
    - 사용자 정의 rule editor 추가
- acknowledge/resolve 상태 추가

    ### Phase 3 — 고도화
    - SLO burn-rate, anomaly detection 도입

    ## 9. 테스트 전략

    - threshold 초과 시 alert 생성 테스트
- 중복 alert suppression 테스트
- resolve/ack state 테스트

    ## 10. 리스크와 대응

    - 오탐이 많으면 신뢰도가 떨어집니다. → suppression window와 severity 단계 도입.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 임계치 기반 경보를 볼 수 있다.
- 경보를 운영자가 triage 할 수 있다.

    ## 12. 후속 확장 아이디어

    - ML anomaly detection
- incident auto-report
