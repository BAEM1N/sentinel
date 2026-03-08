# Sentinel Features

## 1. CLI Agent (`main.py`)

### 대화형 모드
```bash
python main.py
```
- 무한 루프 입력 → 에이전트 실행 → 응답 출력
- `quit`/`exit`: 종료, `clear`: 대화 초기화 (새 thread_id)
- 자동 Langfuse 트레이싱 (lf_config 콜백)

### 단일 질의 모드
```bash
python main.py -q "최근 3일간 트레이스를 분석해주세요"
```

## 2. 트레이스 분석

### list_traces
- 다중 필터: name, user_id, session_id, from_ts, to_ts, tags, limit
- 반환: id, name, timestamp, user_id, latency, total_cost, tokens, tags, level

### get_trace_detail
- 단일 트레이스 심층 조회
- 반환: input/output (1000자 제한), metadata, observations, scores

### list_sessions
- 세션 목록: id, created_at, trace_count

## 3. Metrics API 집계 (`query_metrics`)
- view: traces, observations, scores-numeric
- metrics: count, totalCost, latency, totalTokens
- group_by: name, environment, model 등
- period: hour, day, week, month
- 날짜 범위 + 이름/사용자 필터

## 4. 보고서 생성 (`generate_report`)

### 입력
- `period`: daily / weekly / monthly
- `from_ts`, `to_ts`: ISO8601 날짜 범위 (자동 계산 가능)
- `output_html`: HTML 추가 생성 여부

### 프로세스
1. Langfuse에서 데이터 수집 (`_collect_report_data`)
   - Metrics API: 이름별 count, cost, latency, tokens
   - Trace API: 최근 30건 상세 (이름, 비용, 토큰, 레이턴시)
   - Score API: 평가 스코어 50건
2. REPORT_MD_PROMPT로 LLM 호출 → McKinsey 스타일 MD 생성
3. (옵션) REPORT_HTML_PROMPT → HTML body → report_template.html 삽입
4. `reports/` 디렉토리에 저장

### McKinsey 보고서 구조
```
# LLMOps {기간} 보고서
Executive Summary (3문장)
1. 핵심 지표 (표)
2. 트레이스 분석 (이름별/사용자별/시간대별)
3. 비용 분석 (분포/고비용 TOP 3/최적화 권장)
4. 품질 분석 (스코어/에러 패턴)
5. 권장 조치 (긴급/중요/개선)
부록 (생성 시각, 조회 기간, 데이터 소스)
```

## 5. 프롬프트 관리

### get_langfuse_prompt
- 이름 + 라벨(production/staging)로 조회
- 반환: name, version, label, prompt text, labels

### save_langfuse_prompt
- 새 버전 자동 생성
- 라벨 지정 (staging → 테스트 후 production 승격)

### suggest_prompt_improvement
- 현재 프롬프트 + 관찰된 문제점 입력
- LLM이 원인 분석 → 개선 프롬프트 → 변경 요약 → 예상 효과 출력

## 6. LLM-as-judge 평가

### evaluate_with_llm
- 트레이스 input/output 추출 → 5개 기준 평가
- 기준: 정확성, 완전성, 유용성, 안전성, 일관성 (각 1-5점)
- 종합점수: 0.00~1.00 정규화
- Langfuse에 `llm-judge` 스코어 자동 저장
- 프롬프트 개선 제안 포함

### create_score
- 수동 스코어 기록: trace_id, name, value (0.0~1.0), comment

## 7. FastAPI 웹 서버 (`server.py`)

### 실행
```bash
python server.py              # 개발 (reload)
uvicorn server:app --port 8000  # 프로덕션
```

### 페이지
| 페이지 | URL | 기능 |
|--------|-----|------|
| Dashboard | `/` | KPI 스트립 + 생성 폼 + 최근 보고서 10건 |
| Reports | `/reports` | 전체 보고서 목록 + 아코디언 생성 폼 |
| Report View | `/reports/{name}` | MD: marked.js 렌더링, HTML: iframe/raw |
| Scheduler | `/scheduler` | 크론 잡 상태 + 다음 실행 시간 |

### API
| Endpoint | Method | 기능 |
|----------|--------|------|
| `/api/generate` | POST | 보고서 생성 (period, from_date, to_date, output_html) |
| `/api/scheduler/status` | GET | 스케줄러 상태 JSON |

## 8. APScheduler 자동 보고서

| 잡 | 스케줄 | 기간 |
|----|--------|------|
| daily_report | 매일 00:00 | 전일 00:00~23:59 |
| weekly_report | 매주 월 00:00 | 지난주 월~일 |
| monthly_report | 매월 1일 00:00 | 지난달 전체 |

- MD 항상 생성
- HTML은 `SENTINEL_AUTO_HTML` 환경변수로 제어 (기본 true)
- 생성 후 자동 알림 전송

## 9. 알림 시스템 (`notify.py`)

### Slack
- 환경변수: `SENTINEL_SLACK_WEBHOOK`
- Incoming Webhook → blocks 형식
- 3000자 제한 (초과 시 `...` 절삭)

### Telegram
- 환경변수: `SENTINEL_TELEGRAM_BOT_TOKEN`, `SENTINEL_TELEGRAM_CHAT_ID`
- sendMessage (MD 텍스트, 4000자) + sendDocument (HTML 파일)

### Email (SMTP)
- 환경변수: `SENTINEL_SMTP_HOST/PORT/USER/PASS`, `SENTINEL_EMAIL_TO/FROM`
- HTML 본문 (있으면) 또는 텍스트 + MD 파일 첨부
- STARTTLS 보안

### 통합 디스패처
- `send_report(md_path, html_path)` → 설정된 채널 모두 시도
- 실패 시 에러 로그 출력, 다른 채널은 계속 시도

## 10. 플랫폼 관리

### manage_datasets
- `list`: 데이터셋 목록
- `create`: 새 데이터셋 생성
- `add_item`: 입출력 쌍 추가 (트레이스 소스 연결 가능)
- `list_items`: 데이터셋 아이템 조회

### manage_annotations
- `create`: 트레이스/observation에 코멘트 작성
- `list`: 코멘트 조회

### think_tool
- 전략적 반성 — 에이전트가 분석 전 사고 정리용
