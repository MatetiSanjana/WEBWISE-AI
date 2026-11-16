# Webwise AI

An autonomous web research agent. Enter a topic, pick **Quick** or **Deep** mode, and the app:

1. plans several search queries (Gemini),
2. searches the live web (Tavily) and removes duplicate URLs,
3. has Gemini analyse **only the retrieved sources** and compare them,
4. validates every citation against the sources it actually retrieved,
5. produces a structured, cited report with a PDF download and an evidence-only follow-up chat.

It is built to **never invent research**: if the web search fails you get an error (not a made-up report); thin evidence is
reported as *"Insufficient evidence found."*; unknown citation IDs are stripped; missing publication dates show
*"Date unavailable"*.

> **Honest limits.** This is an AI summarizer, not a fact-checker. Sources are not independently verified, search
> relevance is not credibility, and accuracy is not guaranteed. The "quote located in source" badge proves a quote exists
> in the retrieved text, not that the source is right.

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS 4, Three.js + React Three Fiber, Lucide icons |
| Backend | Python 3.12, FastAPI, Pydantic v2, `tavily-python`, `google-genai`, ReportLab, SQLite |

## Quick start (local)

Prerequisites: **Python 3.11+**, **Node 20+**, a [Tavily](https://app.tavily.com) key and a
[Gemini](https://aistudio.google.com/api-keys) key.

### 1. API keys

Copy the template and fill in your keys. **Edit `.env`, not `.env.example`** (the example file is meant to be shared
and must only ever contain placeholders). `.env` is git-ignored.

```bash
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
```

```ini
TAVILY_API_KEY=tvly-...
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.5-flash-lite
```

Keys are read only by the backend. They are never sent to the browser, never logged (a redaction filter is installed),
and never appear in API responses.

### 2. Backend

```bash
cd backend
python -m venv venv
# Windows:  venv\Scripts\activate        macOS/Linux:  source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Check it: <http://127.0.0.1:8000/api/health> (shows which keys are configured, never their values).

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. In development, Vite proxies `/api` to the backend on port 8000.

---

## Using it

- **Quick Research** – 3 searches, up to 8 sources, concise report (≈ 15–60 s).
- **Deep Research** – 7 searches, up to 18 sources, per-source reading pass, then cross-source comparison (≈ 30 s – 3 min).
- Click any **[S#]** chip in the report to jump to that source. Source cards show title, domain, date (or *Date unavailable*)
  and a clickable URL.
- **Follow-up chat** answers from the stored evidence only and labels each answer *Evidence-based*, *Partially supported*,
  *Not found in this research* or *Unsupported*.
- **Download PDF**, **Save report**, **History**, **Saved Reports**, **Settings** (default mode, background animation).
- Reduced-motion users get a still background automatically; the animation can also be turned off in Settings.

## How "no fake research" is enforced

| Rule | Where |
|---|---|
| Search the web before analysing | `services/pipeline.py` – analysis only starts after Tavily returns usable sources |
| Gemini sees only retrieved text | `services/analyzer.py` – evidence blocks `S1…Sn`; system prompt forbids outside knowledge |
| Source text treated as untrusted (prompt injection) | system prompt rule 9; verified with a live injection test |
| Citation IDs must be real | `services/citations.py` – unknown IDs / inline markers removed; uncited claims moved to "excluded" |
| Quotes must exist in the source | each finding's `supporting_quote` is matched against the cited source text |
| No invented dates | dates only from Tavily metadata, otherwise `Date unavailable` |
| Honest failure | Tavily/Gemini errors surface as clear messages; no report is generated |

## API

| Method & path | Purpose |
|---|---|
| `POST /api/research` | start a task `{topic, mode}` → `{research_id}` (needs `X-Client-Id`, sent automatically by the UI) |
| `GET /api/research/{id}` | status, progress, queries, sources, report, follow-ups |
| `GET /api/research/{id}/report` | structured report (409 until finished) |
| `GET /api/research/{id}/pdf` | PDF download |
| `POST /api/research/{id}/follow-up` | evidence-grounded answer |
| `GET /api/history?saved=` | this browser's research list |
| `POST /api/research/{id}/retry`, `PATCH …/saved`, `DELETE …` | retry, bookmark, delete |
| `GET /api/health` | configuration status |

Interactive docs at `/docs` while `ENABLE_DOCS=true`.

## Tests

```bash
cd backend
pytest -m "not live and not live_deep"     # unit tests, no network, no API usage
pytest -m live -s                           # REAL Tavily + Gemini (uses quota)
pytest -m live_deep -s                      # adds a Deep-mode run
```

Live tests skip themselves when keys are missing. Output of the last live run is written to `backend/data/` for manual
citation checks.

## Configuration reference (`.env`)

| Variable | Default | Notes |
|---|---|---|
| `TAVILY_API_KEY`, `GEMINI_API_KEY` | – | required |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | any model from the [model list](https://ai.google.dev/gemini-api/docs/models) |
| `FRONTEND_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | CORS allow-list |
| `DATABASE_PATH` | `backend/data/webwise.db` | SQLite file |
| `HTTP_TIMEOUT_SECONDS` / `LLM_TIMEOUT_SECONDS` | `45` / `120` | per-call timeouts |
| `RATE_LIMIT_PER_MINUTE` | `10` | per client IP, in memory |
| `ENABLE_DOCS` | `true` | set `false` in production |
| `LOG_LEVEL` | `INFO` | |

## Troubleshooting

- **"daily Gemini quota … is used up"** – free-tier quotas are per model. In testing, `gemini-4-hydrogen` allowed only
  **20 requests/day** (one research uses 2–3), while `gemini-3.5-flash-lite` was fine. Change `GEMINI_MODEL` or enable
  billing, then restart the backend.
- **"Gemini rate limit"** – per-minute limit; wait and press Retry.
- **"Backend unreachable"** – start `uvicorn` (step 2) and check port 8000.
- **Some sources show "Date unavailable"** – Tavily rarely returns publication dates; the app never guesses them.
- **PDF shows boxes instead of non-Latin text** – the PDF uses a system Unicode font (Arial on Windows, DejaVu on Linux:
  `apt install fonts-dejavu-core`). CJK text needs a CJK font.
- After changing `.env`, **restart the backend**.

## Deployment notes

1. **Frontend**: `cd frontend && VITE_API_BASE=https://your-api.example.com npm run build`, then host `frontend/dist`
   on any static host (Vercel, Netlify, Cloudflare Pages…). Serve it with security headers (CSP, `X-Frame-Options`).
2. **Backend**: `uvicorn app.main:app --host 0.0.0.0 --port 8000` behind HTTPS (Render, Railway, Fly.io, a VPS…).
   Set `FRONTEND_ORIGINS` to your site, `ENABLE_DOCS=false`, and put `.env` values in the host's secret store.
3. **Run a single worker.** Jobs run in-process and the rate limiter is in memory; multiple workers would need a shared
   queue/store. Keep `DATABASE_PATH` on a persistent disk.
4. **Privacy model.** The history list is scoped to an anonymous random id the browser stores (`X-Client-Id`), so visitors
   can't browse each other's topics. It is **not authentication**: anyone with a report's unguessable link can open it,
   and clearing browser storage loses your history list. Add real auth before handling sensitive research.
5. Rate limiting keys on the client IP; behind a proxy configure it to forward the real IP (or add a proxy-aware limiter).

## Project structure

```
Webwise AI/
  backend/app/
    main.py            app, CORS, security headers, error handlers
    api/routes.py      endpoints
    services/          planner, search, analyzer, citations, report, pdf, followup, llm, pipeline, modes
    models/db.py       SQLite persistence
    schemas/           Pydantic models (API + LLM output)
    utils/             logging (key redaction), rate limit, URL/text helpers
  backend/tests/       unit + live tests
  frontend/src/
    components/ pages/ hooks/ services/ styles/
  .env.example  .gitignore  README.md
```
