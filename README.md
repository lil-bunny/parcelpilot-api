# ParcelPilot — assessment backend

FastAPI + LangGraph: ReAct tool loop with auth-aware PostgreSQL facts, hybrid document search, service-credit calculation, and confirmation-gated actions.

## Setup

```bash
uv sync
copy .env.example .env   # OPENAI_API_KEY + DATABASE_URL
```

**DATABASE_URL tips:** If your password contains `@`, URL-encode it (`@` → `%40`). On Windows/IPv4-only networks, use the **Session pooler** URI from Supabase (Connect → Session mode, port 5432) — not the direct `db.*.supabase.co` string, which is IPv6-only.

### Seed structured data (Excel → Postgres)

Drop `data/ParcelPilot_Assessment_Data.xlsx` into the repo, then:

```bash
uv run python scripts/verify_schema.py
uv run python scripts/seed_postgres.py
```

### Document pack (hybrid search)

Drop the six assignment PDFs into `artifacts/`, then:

```bash
uv run python scripts/ingest_docs.py   # re-run after catalog.json changes
uv run uvicorn app.main:app --reload
```

```bash
uv run pytest
```

## API (for external UI)

`POST /v1/chat/messages`

```json
{
  "thread_id": "uuid",
  "text": "Can I cancel ORD-1001 without a fee?",
  "user_context": { "role": "customer", "account_id": "ACCT-001" }
}
```

Response includes `text`, `tool_trace`, `confirmation_required`, `proposed_action`, `evidence`, `sources`, `conflicts`, `confidence`.

## Tools

| Tool | Use for |
|------|---------|
| `query_operational_data` | Orders, accounts, tickets (PostgreSQL facts, auth-scoped) |
| `get_applicable_rules` | Order-specific rules: Postgres order→account→contract_file, then filtered agreement + SOP |
| `search_documents` | General policy/SLA/product docs (requires filters for customer agreements) |
| `calculate_service_credit` | Eligibility math from facts + evidence |
| `create_escalation` / `update_ticket` / `create_followup` | Writes — require explicit user confirmation |

## Architecture

`model ⇄ tools` with action confirmation gate. Operational facts never come from vector search; policy text never comes from Postgres.

## Deploy on Render

1. Push repo to GitHub; in Render: **New → Blueprint** and select `render.yaml`, or **New → Web Service** manually.
2. Set **secret** env vars in the Render dashboard:
   - `OPENAI_API_KEY`
   - `DATABASE_URL` (Supabase **Session pooler** URI)
3. Optional: `CORS_ORIGINS` — add your deployed MVP-UI URL (comma-separated).
4. **Chroma / policy search:** drop the six PDFs into `artifacts/` before deploy so `render_build.sh` runs ingest at build time. Check `GET /v1/health` → `chroma_ready: true`.
5. Without PDFs, the API still runs (orders, tickets, escalation); policy tools return empty until indexed.

**Manual commands** (same as `render.yaml`):

```bash
# Build
bash scripts/render_build.sh
# Start
uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Persistent Chroma (optional):** attach a Render disk at `/var/data`, set `CHROMA_DIR=/var/data/chroma`, run ingest once via shell.
