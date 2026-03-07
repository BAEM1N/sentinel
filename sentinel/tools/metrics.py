"""Metrics API 집계 · 보고서 생성 도구."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from langchain.tools import tool

from sentinel.config import lf_client, model


def _default_range(days_back: int = 7):
    """기본 날짜 범위를 반환합니다."""
    now = datetime.utcnow()
    return (
        (now - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


@tool
def query_metrics(
    view: str = "traces",
    metrics: str = "count,totalCost,latency",
    group_by: str = "name",
    period: str = "day",
    from_ts: str = "",
    to_ts: str = "",
    filter_name: str = "",
    filter_user_id: str = "",
) -> str:
    """Langfuse Metrics API로 집계 분석을 수행합니다.

    Args:
        view: 조회 대상 (traces, observations, scores-numeric)
        metrics: 집계 지표 (쉼표 구분: count, totalCost, latency, totalTokens)
        group_by: 그룹핑 차원 (name, environment, model 등)
        period: 시간 단위 (hour, day, week, month)
        from_ts: 시작 날짜 (ISO8601, 비우면 최근 7일)
        to_ts: 종료 날짜 (ISO8601, 비우면 현재)
        filter_name: 트레이스 이름 필터
        filter_user_id: 사용자 ID 필터
    """
    if not from_ts or not to_ts:
        default_from, default_to = _default_range(7)
        from_ts = from_ts or default_from
        to_ts = to_ts or default_to

    agg_map = {
        "count": "count",
        "totalCost": "sum",
        "latency": "p50",
        "totalTokens": "sum",
    }
    metric_list = [
        {"measure": m.strip(), "aggregation": agg_map.get(m.strip(), "sum")}
        for m in metrics.split(",")
    ]

    q: dict = {
        "view": view,
        "dimensions": [{"field": group_by}],
        "metrics": metric_list,
        "timeDimension": {"granularity": period},
        "fromTimestamp": from_ts,
        "toTimestamp": to_ts,
        "filters": [],
        "orderBy": [],
        "rowLimit": 100,
    }
    if filter_name:
        q["filters"].append(
            {"column": "name", "operator": "equals", "value": filter_name, "type": "string"}
        )
    if filter_user_id:
        q["filters"].append(
            {"column": "userId", "operator": "equals", "value": filter_user_id, "type": "string"}
        )

    result = lf_client.api.metrics.metrics(query=json.dumps(q))
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# HTML 보고서 프롬프트
# ---------------------------------------------------------------------------

REPORT_HTML_PROMPT = """당신은 시니어 LLM 엔지니어이자 데이터 분석가입니다.
아래 Langfuse 데이터를 기반으로 **{period_kr} LLMOps 보고서**의 HTML 본문을 생성하세요.

**기간:** {from_ts} ~ {to_ts}

## 원시 데이터 (Metrics API)
{metrics_json}

## 트레이스 상세 샘플
{traces_json}

## 스코어 현황
{scores_json}

---

아래 HTML 구조를 **정확히** 따라 작성하세요. CSS 클래스는 이미 정의되어 있으므로 그대로 사용하세요.
수치는 반드시 데이터에서 추출하세요. 데이터에 없는 수치를 지어내지 마세요.

```html
<div class="report-header">
  <h1>LLMOps {period_kr} 보고서</h1>
  <div class="subtitle">{date_label}</div>
  <div class="meta">
    <div class="meta-item"><span class="meta-dot dot-green"></span> 총 트레이스: N건</div>
    <div class="meta-item"><span class="meta-dot dot-blue"></span> 총 비용: $N.NN</div>
    <div class="meta-item"><span class="meta-dot dot-amber"></span> 활성 사용자: N명</div>
  </div>
</div>

<div class="summary-box">
  <h2>Executive Summary</h2>
  <ul>
    <li>핵심 인사이트 1</li>
    <li>핵심 인사이트 2</li>
    <li>핵심 인사이트 3</li>
  </ul>
</div>

<h2 class="section-title">1. 핵심 지표 대시보드</h2>
<div class="kpi-grid">
  <div class="kpi-card highlight">
    <div class="kpi-value">N</div>
    <div class="kpi-label">총 트레이스</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value">$N.NN</div>
    <div class="kpi-label">총 비용</div>
    <div class="kpi-sub">avg $N.NN/trace</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value">N</div>
    <div class="kpi-label">총 토큰</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value">N.Ns</div>
    <div class="kpi-label">P50 레이턴시</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value">N.Ns</div>
    <div class="kpi-label">P95 레이턴시</div>
  </div>
  <div class="kpi-card warning/danger (에러율에 따라)">
    <div class="kpi-value">N건</div>
    <div class="kpi-label">에러/이상 트레이스</div>
    <div class="kpi-sub">N% of total</div>
  </div>
</div>

<h2 class="section-title">2. 트레이스 분석</h2>
<h3>2.1 이름별 분포</h3>
<table>
  <thead><tr><th>트레이스 이름</th><th>호출 수</th><th>비용 합계</th><th>평균 비용</th><th>P50 레이턴시</th><th>토큰 합계</th></tr></thead>
  <tbody>
    <tr><td>이름</td><td class="num">N</td><td class="num cost">$N.NN</td><td class="num">$N.NN</td><td class="num latency">N.Ns</td><td class="num">N</td></tr>
    <!-- 상위 10개 -->
  </tbody>
</table>

<h3>2.2 사용자별 사용량</h3>
<table>
  <thead><tr><th>사용자 ID</th><th>트레이스 수</th><th>총 비용</th><th>평균 레이턴시</th></tr></thead>
  <tbody>
    <tr><td>user_id</td><td class="num">N</td><td class="num cost">$N.NN</td><td class="num latency">N.Ns</td></tr>
  </tbody>
</table>

<h3>2.3 시간대별 트렌드</h3>
<p>시간/일자별 호출량 변화를 텍스트로 분석하세요.</p>

<h2 class="section-title">3. 비용 분석</h2>
<h3>3.1 비용 분포</h3>
<table>
  <thead><tr><th>지표</th><th>값</th></tr></thead>
  <tbody>
    <tr><td>최솟값</td><td class="num cost">$N.NN</td></tr>
    <tr><td>최댓값</td><td class="num high-cost">$N.NN</td></tr>
    <tr><td>평균</td><td class="num cost">$N.NN</td></tr>
    <tr><td>중앙값</td><td class="num cost">$N.NN</td></tr>
  </tbody>
</table>

<h3>3.2 고비용 트레이스 TOP 3</h3>
<table>
  <thead><tr><th>#</th><th>트레이스 이름</th><th>날짜</th><th>비용</th><th>토큰</th></tr></thead>
  <tbody>
    <tr><td>1</td><td>이름</td><td>날짜</td><td class="num high-cost">$N.NN</td><td class="num">N</td></tr>
  </tbody>
</table>

<h3>3.3 비용 최적화 권장</h3>
<div class="alert alert-info"><strong>권장:</strong> 구체적 비용 절감 방안</div>

<h2 class="section-title">4. 품질 분석</h2>
<h3>4.1 스코어 현황</h3>
<!-- 스코어가 있으면 표, 없으면 안내 메시지 -->
<table>
  <thead><tr><th>스코어명</th><th>건수</th><th>평균</th><th>최솟값</th><th>최댓값</th></tr></thead>
  <tbody>...</tbody>
</table>

<h3>4.2 에러/이상 패턴</h3>
<div class="alert alert-warning"><strong>이상 패턴:</strong> 분석 내용</div>

<h2 class="section-title">5. 권장 조치</h2>
<ul class="action-list">
  <li class="alert-critical"><span class="badge badge-critical">긴급</span> 조치 내용</li>
  <li class="alert-warning"><span class="badge badge-important">중요</span> 조치 내용</li>
  <li class="alert-info"><span class="badge badge-improve">개선</span> 조치 내용</li>
</ul>

<h2 class="section-title">6. 부록</h2>
<p class="text-muted">보고서 생성 시각, 조회 기간, 데이터 소스, 총 Metrics API row 수 등</p>
```

**중요 규칙:**
- HTML만 출력하세요 (```html 코드 블록 없이, 순수 HTML만)
- CSS 클래스를 정확히 사용하세요 (kpi-card, cost, high-cost, latency, num, alert-*, badge-* 등)
- 비용은 달러 표시, 천 단위 구분자 사용
- 레이턴시 단위는 초(s)
- 데이터가 없는 항목은 "N/A" 또는 "데이터 없음"으로 표시
"""


def _load_template() -> str:
    """HTML 템플릿을 로드합니다."""
    tpl_path = Path(__file__).parent.parent / "report_template.html"
    return tpl_path.read_text(encoding="utf-8")


def _collect_report_data(from_ts: str, to_ts: str, gran: str):
    """보고서용 데이터를 수집합니다."""
    # 1) Metrics API
    metrics_q = json.dumps({
        "view": "traces",
        "dimensions": [{"field": "name"}],
        "metrics": [
            {"measure": "count", "aggregation": "count"},
            {"measure": "totalCost", "aggregation": "sum"},
            {"measure": "latency", "aggregation": "p50"},
            {"measure": "latency", "aggregation": "p95"},
            {"measure": "totalTokens", "aggregation": "sum"},
        ],
        "timeDimension": {"granularity": gran},
        "fromTimestamp": from_ts,
        "toTimestamp": to_ts,
        "filters": [],
        "orderBy": [],
        "rowLimit": 100,
    })
    metrics_data = lf_client.api.metrics.metrics(query=metrics_q)

    # 2) 트레이스 샘플
    from_dt = datetime.fromisoformat(from_ts.replace("Z", "+00:00"))
    to_dt = datetime.fromisoformat(to_ts.replace("Z", "+00:00"))
    traces_res = lf_client.api.trace.list(limit=30, from_timestamp=from_dt, to_timestamp=to_dt)
    traces_data = traces_res.data if hasattr(traces_res, "data") else traces_res
    traces_summary = [
        {
            "name": getattr(t, "name", None),
            "user_id": getattr(t, "user_id", None),
            "session_id": getattr(t, "session_id", None),
            "latency": getattr(t, "latency", None),
            "total_cost": getattr(t, "total_cost", None),
            "input_tokens": getattr(t, "input_tokens", None),
            "output_tokens": getattr(t, "output_tokens", None),
            "tags": getattr(t, "tags", []),
            "level": getattr(t, "level", None),
            "timestamp": str(getattr(t, "timestamp", ""))[:19],
        }
        for t in traces_data
    ]

    # 3) 스코어
    try:
        scores_res = lf_client.api.score_v_2.get(limit=50, from_timestamp=from_dt, to_timestamp=to_dt)
        scores_data = scores_res.data if hasattr(scores_res, "data") else scores_res
        scores_summary = [
            {"name": s.name, "value": s.value, "trace_id": getattr(s, "trace_id", None)}
            for s in scores_data
        ]
    except Exception:
        scores_summary = []

    return (
        json.dumps(metrics_data, default=str, indent=2),
        json.dumps(traces_summary, default=str, ensure_ascii=False, indent=2),
        json.dumps(scores_summary, default=str, ensure_ascii=False, indent=2),
    )


@tool
def generate_report(
    period: str = "daily", from_ts: str = "", to_ts: str = "",
    format: str = "html",
) -> str:
    """일간/주간/월간 LLMOps 보고서를 생성합니다.

    Args:
        period: 보고서 주기 (daily, weekly, monthly)
        from_ts: 시작 날짜 (ISO8601, 비우면 자동 계산)
        to_ts: 종료 날짜 (ISO8601, 비우면 오늘)
        format: 출력 형식 (html 또는 markdown)
    """
    now = datetime.utcnow()
    if not to_ts:
        to_ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    if not from_ts:
        delta = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 1)
        from_ts = (now - timedelta(days=delta)).strftime("%Y-%m-%dT%H:%M:%SZ")

    gran = {"daily": "hour", "weekly": "day", "monthly": "week"}.get(period, "day")
    period_kr = {"daily": "일간", "weekly": "주간", "monthly": "월간"}.get(period, period)
    date_label = f"{from_ts[:10]} ~ {to_ts[:10]}"
    generated_at = now.strftime("%Y-%m-%d %H:%M UTC")

    metrics_json, traces_json, scores_json = _collect_report_data(from_ts, to_ts, gran)

    prompt = REPORT_HTML_PROMPT.format(
        period_kr=period_kr,
        from_ts=from_ts,
        to_ts=to_ts,
        date_label=date_label,
        metrics_json=metrics_json,
        traces_json=traces_json,
        scores_json=scores_json,
    )
    resp = model.invoke(prompt)
    html_content = resp.content

    # ```html ... ``` 블록이 있으면 추출
    import re
    code_match = re.search(r"```html\s*(.*?)```", html_content, re.DOTALL)
    if code_match:
        html_content = code_match.group(1).strip()

    if format == "markdown":
        return html_content

    # HTML 템플릿에 삽입
    template = _load_template()
    title = f"LLMOps {period_kr} 보고서 - {date_label}"
    full_html = (
        template
        .replace("{{title}}", title)
        .replace("{{content}}", html_content)
        .replace("{{generated_at}}", generated_at)
    )

    # 파일 저장
    reports_dir = os.environ.get("SENTINEL_REPORTS_DIR", "./reports")
    os.makedirs(reports_dir, exist_ok=True)
    filename = f"{period}_report_{from_ts[:10]}.html"
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_html)

    return f"보고서 저장 완료: {filepath}\n\n{full_html}"
