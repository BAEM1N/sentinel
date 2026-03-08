# Sentinel Frontend Reference

## Design System: Swiss Editorial Data

모노크롬, 타이포그래피 중심의 데이터 대시보드 디자인. "바이브코딩"을 배제한 깔끔한 컨설팅 스타일.

## Stack
- **Tailwind CSS**: CDN (`<script src="https://cdn.tailwindcss.com">`)
- **Pretendard Variable**: 한국어 최적화 가변 웹폰트, CDN
- **marked.js**: MD → HTML 렌더링 (report_view.html에서 사용)
- **Jinja2**: 서버사이드 템플릿 (FastAPI)
- **No JS framework**: 바닐라 JS만 사용

## Tailwind Custom Config

```javascript
tailwind.config = {
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Pretendard Variable"', 'Pretendard', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'Helvetica Neue', 'sans-serif'],
        mono: ['"SF Mono"', 'Consolas', '"Liberation Mono"', 'Menlo', 'monospace'],
      },
      colors: {
        ink: { DEFAULT: '#111', light: '#444', muted: '#888', faint: '#bbb', wash: '#f7f7f7' },
        rule: { DEFAULT: '#e0e0e0', dark: '#111' },
      },
      fontSize: {
        '2xs': ['0.65rem', { lineHeight: '1' }],
      },
    },
  },
}
```

## Color Palette

| 토큰 | HEX | 용도 |
|------|-----|------|
| `ink` | `#111` | 본문 텍스트, 네비 활성 |
| `ink-light` | `#444` | 부제목, hover |
| `ink-muted` | `#888` | 메타 텍스트, 라벨 |
| `ink-faint` | `#bbb` | 비활성, 푸터 |
| `ink-wash` | `#f7f7f7` | hover 배경 |
| `rule` | `#e0e0e0` | 보더, 구분선 |
| `rule-dark` | `#111` | 강조 보더 |

## Typography

| 용도 | 크기 | 무게 | 트래킹 |
|------|------|------|--------|
| 페이지 제목 | 22px | bold | -0.03em |
| KPI 숫자 | 32px | bold | -0.04em |
| 라벨 | 2xs (0.65rem) | semibold | 0.08~0.1em, uppercase |
| 테이블 헤더 | 2xs | semibold | 0.08em, uppercase |
| 본문 | 13px | normal | — |
| 로고 | sm | bold | -0.02em, uppercase |

## Template Structure

### base.html
```
<html>
  <head>
    Pretendard CDN
    Tailwind CDN + custom config
    Custom CSS (scrollbar, nav-link.active, row-animate, form focus)
  </head>
  <body class="bg-white text-ink font-sans min-h-screen flex flex-col">
    <nav> — 960px, 12h, border-b
      Logo (SENTINEL) | Dashboard | Reports | Scheduler | "LLMOps Agent"
    </nav>
    <main> — 960px, flex-1, py-8
      {% block content %}
    </main>
    <footer> — 960px, 10h, border-t
      "Sentinel v0.0.1" | "Powered by Langfuse"
    </footer>
  </body>
</html>
```

### index.html (Dashboard)
```
Header: "Dashboard" | "N reports on file"
KPI Strip: 3-col grid, border, 32px bold numbers
  - Total Reports | Markdown | HTML
Generate Report Form: border box
  - Period (select) | From (date) | To (date) | +HTML (checkbox) | Generate (btn)
Recent Reports: table (최근 10건)
  - Name (link) | Type (badge) | Size | Modified
```

### reports.html
```
Header: "Reports" | "N total"
Generate Form: <details> 아코디언
Full Table: period, name, type, size, modified, download
```

### report_view.html
```
Header: filename | Raw 다운로드 링크
Content:
  - MD: <div id="md-target"> + marked.js 렌더링
  - HTML: iframe 또는 raw HTML
```

### scheduler.html
```
Header: "Scheduler" | Running/Stopped indicator
Job Table: ID | Schedule | Next Run
Schedule Summary: 3-col grid (Daily/Weekly/Monthly 설명)
```

## Key CSS Patterns

### Navigation Active State
```css
.nav-link.active { color: #111; }
.nav-link.active::after {
  content: '';
  position: absolute;
  bottom: -17px;  /* nav border-b 위에 겹침 */
  left: 0; right: 0;
  height: 1.5px;
  background: #111;
}
```

### Table Row Animation
```css
@keyframes rowIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
.row-animate { animation: rowIn 0.2s ease-out both; }
/* style="animation-delay: {{ loop.index0 * 30 }}ms" */
```

### Form Elements
```css
select, input { font-family: inherit; outline: none; }
select:focus, input:focus { border-color: #111 !important; }
/* rounded-none, border-rule 스타일 */
```

## Report Template (report_template.html)

A4 인쇄용 McKinsey 스타일 HTML 보고서. 웹 UI와 별도.

### 특징
- `@page { size: A4; margin: 24mm 20mm; }`
- `@media print` — 그림자 제거, 마진 조정
- Pretendard 폰트 (CDN)
- 플레이스홀더: `{{title}}`, `{{content}}`, `{{generated_at}}`

## Jinja2 Context Variables

| 페이지 | 변수 | 타입 |
|--------|------|------|
| 공통 | `active_page` | str: dashboard/reports/scheduler |
| index | `total`, `md_count`, `html_count` | int |
| index | `reports` | list[dict] (최근 10건) |
| reports | `reports` | list[dict] (전체) |
| report_view | `filename`, `content`, `is_html` | str, str, bool |
| scheduler | `running`, `jobs` | bool, list[dict] |

## marked.js Integration (report_view.html)

```javascript
// 안전한 방법: Jinja2 tojson 필터로 JS 변수에 주입
(function() {
  const raw = {{ content|tojson }};
  document.getElementById('md-target').innerHTML = marked.parse(raw);
})();
```

### MD 렌더링 CSS (report_view.html 내장)
- 테이블: 전체 너비, 보더, 헤더 배경 #111
- 코드 블록: 배경 #f7f7f7, 보더, 모노 폰트
- 블록쿼트: 왼쪽 2px 보더 #111, 이탤릭
- 헤딩: h1 20px bold, h2 16px bold (밑줄), h3 14px semibold
- 리스트: disc/decimal, 들여쓰기 20px
