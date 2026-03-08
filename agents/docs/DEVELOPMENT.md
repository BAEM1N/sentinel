# Sentinel Development Guide

## Quick Start

```bash
cd D:\sentinel

# 가상환경
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[all-providers]"

# 환경변수
cp .env.example .env
# .env에 OPENAI_API_KEY, LANGFUSE_* 설정

# CLI 실행
python main.py

# 웹 서버 실행
python server.py
# → http://localhost:8000
```

## Code Conventions

### 언어
- **코드**: 영어 (변수명, 함수명, 클래스명)
- **문서/주석/독스트링**: 한국어
- **print 메시지**: 영어 ASCII만 사용 (Windows cp949 인코딩 에러 방지)

### 패턴
- `@tool` 데코레이터: 모든 에이전트 도구는 `langchain.tools.tool`로 정의
- Langfuse API: `lf_client.api.{resource}.{method}()` 패턴
- 결과 반환: JSON 문자열 (`json.dumps()`)
- 날짜: ISO8601 형식 (`YYYY-MM-DDTHH:MM:SSZ`)
- 환경변수: `os.environ.get("SENTINEL_*", default)`
- 모델 호출: `model.invoke(prompt)` → `resp.content`

### 프론트엔드
- Tailwind CSS via CDN (`<script src="https://cdn.tailwindcss.com">`)
- Pretendard Variable 웹폰트 via CDN
- 디자인 시스템: "Swiss Editorial Data" — 모노크롬, 타이포그래피 중심
- 커스텀 컬러: `ink` (텍스트), `rule` (보더)
- 마크다운 렌더링: marked.js CDN
- 네비게이션: `active_page` 컨텍스트로 현재 페이지 하이라이트

## Known Issues & Fixes

### 1. langchain 1.2 CallbackHandler Import 에러
**문제**: `from langchain.callbacks import CallbackHandler` 실패 — langchain 1.2에서 callbacks가 langchain_core로 이동
**해결**: langfuse의 `from langfuse.langchain import CallbackHandler`를 try/except로 감싸서 방어적 임포트

```python
langfuse_handler = None
if os.environ.get("LANGFUSE_SECRET_KEY"):
    try:
        from langfuse.langchain import CallbackHandler
        langfuse_handler = CallbackHandler()
    except (ImportError, ModuleNotFoundError):
        pass
```

### 2. Windows cp949 인코딩 에러
**문제**: `UnicodeEncodeError` — 한국어 em dash `—` 같은 유니코드 문자를 print할 때 cp949 코덱이 처리 못함
**해결**: 서버/스케줄러의 print 메시지를 영어 ASCII로 변경

```python
# BAD:  print("[sentinel] 스케줄러 시작됨 — 일간(00:00)")
# GOOD: print("[sentinel] scheduler started: daily(00:00)")
```

### 3. Port 충돌 (WinError 10013)
**문제**: 8000번 포트가 이미 사용 중
**해결**: 다른 포트 사용 (예: 8585) 또는 기존 프로세스 종료

### 4. marked.js MD 렌더링 에러
**문제**: `<template>` 태그 접근 시 `TypeError: Cannot read properties of null`, 스크립트 중복 시 `Identifier 'raw' has already been declared`
**해결**: `{{ content|tojson }}` Jinja2 필터로 안전하게 JS 변수에 주입, 단일 IIFE 블록 사용

```javascript
(function() {
  const raw = {{ content|tojson }};
  document.getElementById('md-target').innerHTML = marked.parse(raw);
})();
```

### 5. APScheduler AsyncIOScheduler와 동기 함수
**주의**: 스케줄러의 잡 함수(`_job_daily` 등)는 동기 함수지만, `AsyncIOScheduler`에서 잘 동작함 (APScheduler가 내부적으로 스레드풀에서 실행)
**향후**: 비동기로 전환하려면 `async def`로 바꾸고 `await model.ainvoke()` 사용

## Design Decisions

### 보고서: MD 기본 + HTML 옵션
- **이유**: MD는 가볍고 버전 관리/diff에 유리, HTML은 시각적 프레젠테이션용
- **구현**: `generate_report(output_html=False)` — MD 항상 저장, HTML은 옵션
- **프롬프트**: MD와 HTML은 별도 프롬프트 (`REPORT_MD_PROMPT`, `REPORT_HTML_PROMPT`)
- **스케줄러**: `SENTINEL_AUTO_HTML` env var로 제어 (기본 true)

### McKinsey 컨설팅 스타일
- **톤**: 간결, 전문적, 수식어 배제
- **구조**: Executive Summary → 핵심 지표 → 트레이스 분석 → 비용 분석 → 품질 분석 → 권장 조치
- **디자인**: 모노크롬, 다크 테이블 헤더, 보더 기반 KPI 그리드, 배지 기반 알림 등급
- **원칙**: "데이터에 없는 수치를 지어내지 마세요"

### 멀티 프로바이더 전략
- **네이티브**: openai (ChatOpenAI), anthropic (ChatAnthropic), gemini (ChatGoogleGenerativeAI), ollama (ChatOllama)
- **OpenAI 호환**: vllm, lmstudio, openrouter, qwen, glm — 모두 ChatOpenAI + base_url
- **팩토리**: `_create_model(provider, model)` — 런타임에 프로바이더 선택
- **폴백**: `ModelFallbackMiddleware(fallback)` — 1차 모델 실패 시 자동 전환

### Swiss Editorial Data 디자인
- **컬러**: ink (#111 계열), rule (#e0e0e0 계열) — 장식 없는 모노크롬
- **타이포**: Pretendard Variable, -0.03em tracking, 32px bold 숫자
- **컴포넌트**: 보더 기반 KPI 스트립, rounded-none 인풋, row-animate 테이블
- **원칙**: "과도한 바이브코딩스러운 시스템 디자인 회피"

### 알림 시스템
- **통합 디스패처**: `send_report()` — 설정된 채널만 자동 실행
- **Slack**: Webhook → blocks 형식 (3000자 제한)
- **Telegram**: sendMessage (텍스트) + sendDocument (HTML 파일)
- **Email**: SMTP + STARTTLS → HTML body 또는 텍스트 + MD 첨부

## Git Info

- **GitHub**: https://github.com/BAEM1N/sentinel
- **Branch**: main
- **Account**: BAEM1N

### Commit History
```
859f6d3 feat: Pretendard 웹폰트 + 프론트엔드 전면 리디자인
954d616 docs: README 업데이트 — 웹 서버, 스케줄러, 알림 문서화
fafd6e7 feat: FastAPI 서버 + 스케줄러 + 알림 + 웹 UI
886af02 feat: McKinsey 스타일 보고서 + 멀티 프로바이더 마무리
b84a18d feat: Sentinel LLMOps Agent v0.0.1 — initial release
```
