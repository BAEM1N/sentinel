# AF-02 Saved Analysis Playbooks

    - 영역: Agent
    - 분류: 신규기능
    - 우선순위: 중간
    - 상태: 제안 문서

    ## 1. 이 문서가 다루는 기능/개선이 무엇인가

    운영자가 반복적으로 수행하는 분석 시나리오를 템플릿/플레이북으로 저장하고 재실행할 수 있게 만드는 기능입니다. 예: 최근 7일 비용 급증 분석, 특정 release 회귀 점검, 저점수 trace 수집 보고서.

    ## 2. 왜 필요한가

    실제 LLMOps 운영은 반복되는 질문의 집합입니다. 매번 자유 질의로 같은 분석을 다시 쓰게 하면 품질과 재현성이 떨어집니다.

    ## 3. 현재 코드 기준 진단

    - 현재는 자유 질의형 CLI/agent 사용 방식입니다.
- 반복 분석을 재사용할 수 있는 템플릿 저장소가 없습니다.
- 보고서 스케줄은 있지만 분석 논리 자체가 플레이북으로 구조화되어 있지 않습니다.

    ### 관련 코드/근거

    - `main.py:22-80`
- `sentinel/prompts.py:12-31`
- `sentinel/tools/metrics.py:397-474`

    ## 4. 목표 상태

    운영팀이 분석 패턴을 저장해두고, 파라미터만 바꿔 반복 실행할 수 있는 상태를 목표로 합니다.

    ## 5. 포함 범위 / 제외 범위

    ### 포함 범위
    - playbook 저장 형식
- 파라미터화된 실행
- playbook 실행 이력
- 기본 내장 playbook 몇 종

    ### 제외 범위
    - 완전한 no-code workflow builder

    ## 6. 상세 요구사항

    ### 기능 요구사항
    - playbook은 이름, 설명, 질의 템플릿, 파라미터 정의를 가져야 합니다.
- CLI 또는 API에서 playbook id + parameter로 실행할 수 있어야 합니다.
- playbook 실행 결과를 run history와 연결해야 합니다.

    ### 비기능 요구사항
    - YAML/JSON 파일 기반으로 관리 가능해야 합니다.
- 기본 플레이북은 버전 관리가 쉬워야 합니다.

    ## 7. 개발 설계

    ### 변경 대상 모듈
    - 신규 `sentinel/playbooks/`
- `main.py`
- 향후 웹 UI와 연동

    ### 권장 디렉터리/파일 구조
    ```text
sentinel/
├── playbooks/
│   ├── registry.py
│   ├── runner.py
│   └── builtins/
│       ├── cost_spike.yaml
│       └── release_regression.yaml
```

    ### 데이터/제어 흐름
    1. 운영자가 playbook을 선택합니다.
2. 필수 파라미터를 입력합니다.
3. playbook runner가 질의 템플릿과 파라미터를 조합합니다.
4. agent 실행 후 결과와 run_id를 저장합니다.

    ### API / CLI / 내부 계약 초안
    - `PlaybookDefinition`
- `run_playbook(name, params)`
- `list_playbooks()`

    ## 8. 단계별 개발 방법

    ### Phase 1 — 최소 동작 구현
    - 파일 기반 playbook registry를 만듭니다.
- CLI에서 playbook 실행을 지원합니다.
- 내장 playbook 2~3개를 추가합니다.

    ### Phase 2 — 운영 가능한 형태로 보강
    - 실행 이력과 파라미터 기록을 남깁니다.
- 보고서 생성 서비스와 연계합니다.

    ### Phase 3 — 고도화
    - 웹 UI에서 playbook 실행/스케줄링을 지원합니다.
- 조직 내 공유 playbook 기능을 추가합니다.

    ## 9. 테스트 전략

    - playbook 파라미터 검증 테스트
- registry load 테스트
- 내장 playbook regression 테스트

    ## 10. 리스크와 대응

    - 플레이북이 너무 많아지면 관리가 어려워집니다. → owner, version, tags 메타데이터를 둡니다.

    ## 11. 완료 기준 (Acceptance Criteria)

    - 반복 분석이 자유 질의가 아닌 재사용 가능한 단위로 관리된다.
- playbook 실행 이력이 남는다.

    ## 12. 후속 확장 아이디어

    - playbook marketplace
- scheduled playbook runs
