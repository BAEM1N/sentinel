# Agent 문서 인덱스

이 폴더는 Sentinel의 **Agent / Backend / Core Orchestration** 관점 개선안과 신규 기능 제안을 기능별 파일로 정리한 문서 모음입니다.

## 읽는 순서 권장

1. 개선 우선순위가 높은 문서부터
2. 이후 신규 기능 문서
3. 마지막으로 웹 문서와 연결해 전체 제품 로드맵 확인

## 개선 문서

- [AG-01 프로바이더별 Fallback 모델 전략 정교화](./AG-01-provider-fallback-model-strategy.md)
- [AG-02 외부 API 호출 복원력 계층](./AG-02-external-api-resilience.md)
- [AG-03 Prompt Injection 및 데이터 오염 방어](./AG-03-prompt-injection-defense.md)
- [AG-04 도구 출력의 구조화 및 스키마화](./AG-04-structured-tool-output.md)
- [AG-05 보고서 생성 로직 단일 서비스화](./AG-05-report-service-unification.md)
- [AG-06 영속 Checkpoint와 작업공간 분리](./AG-06-persistent-checkpoint-workspace.md)
- [AG-07 쓰기/변경 Tool에 대한 HITL 승인 계층](./AG-07-hitl-mutation-approval.md)
- [AG-08 조회 필터 확장과 대용량 Trace 처리](./AG-08-query-filter-expansion-large-trace.md)
- [AG-09 CLI 복원력 및 운영자 UX 고도화](./AG-09-cli-resilience-operator-ux.md)

## 신규 기능 문서

- [AF-01 Persistent Run History 및 Audit Log](./AF-01-persistent-run-history-audit-log.md)
- [AF-02 Saved Analysis Playbooks](./AF-02-saved-analysis-playbooks.md)
- [AF-03 Batch Evaluation Runner](./AF-03-batch-evaluation-runner.md)
