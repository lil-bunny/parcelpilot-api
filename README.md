# ParcelPilot API

FastAPI + LangGraph support agent. Query in → model picks tools → ToolNode runs them → final answer with a `tool_trace`.

Live API: `https://parcelpilot-api-cvki.onrender.com`  
Health: `https://parcelpilot-api-cvki.onrender.com/v1/health`

UI is a separate repo: [parcelpilot-ui](https://github.com/lil-bunny/parcelpilot-ui).

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- An OpenAI API key
- Postgres (Supabase **Session pooler** URI on port 5432 works; the direct `db.*.supabase.co` host is IPv6-only)

## Run locally

```bash
git clone https://github.com/lil-bunny/parcelpilot-api.git
cd parcelpilot-api
uv sync
cp .env.example .env          # Windows: copy .env.example .env
```

Edit `.env`:

```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

If the password contains `@ : / ? #`, URL-encode it (`@` → `%40`).

```bash
uv run uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Health: http://127.0.0.1:8000/v1/health (`chroma_ready` is `true` after PDFs are ingested)
- Docs: http://127.0.0.1:8000/docs

### Optional: seed Postgres from Excel

Put `ParcelPilot_Assessment_Data.xlsx` in `data/`, then:

```bash
uv run python scripts/verify_schema.py
uv run python scripts/seed_postgres.py
```

### Optional: policy PDFs (hybrid search)

Put the six assignment PDFs in `artifacts/`, then:

```bash
uv run python scripts/ingest_docs.py
```

Without PDFs, orders/tickets/escalation still work. Policy tools return empty until indexed.

## Run with the UI

In a second terminal, clone and start [parcelpilot-ui](https://github.com/lil-bunny/parcelpilot-ui):

```bash
git clone https://github.com/lil-bunny/parcelpilot-ui.git
cd parcelpilot-ui
npm install
# leave VITE_API_BASE empty so Vite proxies /v1 → localhost:8000
npm run dev
```

Open http://localhost:5173 — mock login `ACCT-001` / `demo`.

## Smoke test (API only)

```bash
curl -s http://127.0.0.1:8000/v1/health
curl -s http://127.0.0.1:8000/v1/tools
curl -s -X POST http://127.0.0.1:8000/v1/chat/messages \
  -H "Content-Type: application/json" \
  -d "{\"thread_id\":\"t1\",\"text\":\"What is the status of ORD-1001?\",\"user_context\":{\"role\":\"customer\",\"account_id\":\"ACCT-001\"}}"
```

## Tests

```bash
uv run pytest
```

## Tools

| Tool | Use for |
|------|---------|
| `query_operational_data` | Orders, accounts, tickets (Postgres, auth-scoped) |
| `get_applicable_rules` | Order-specific rules from agreement + SOP |
| `search_documents` | General policy/SLA/product docs |
| `calculate_service_credit` | Eligibility math from facts + evidence |
| `create_escalation` / `update_ticket` / `create_followup` | Writes — need explicit user confirmation |

Operational facts never come from vector search; policy text never comes from Postgres.

## Deploy on Render

`render.yaml` is the blueprint.

1. Set secrets: `OPENAI_API_KEY`, `DATABASE_URL` (session pooler).
2. Set `CORS_ORIGINS` to your UI origin(s), comma-separated (include `http://localhost:5173` for local UI).
3. Drop PDFs into `artifacts/` before deploy if you want policy search (`GET /v1/health` → `chroma_ready: true`).
