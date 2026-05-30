# Kodrlytics — Financial Analysis Engine for German Companies

A deterministic financial analysis tool that ingests company financial statements,
computes 22+ ratios, benchmarks against sector peers, generates improvement
recommendations with projected outcomes, and visualizes the entire pipeline live
in 3D.

**Core guarantee:** The LLM never does math. Every number is computed in
deterministic Python and traceable to a formula. The LLM is used only for
(1) extracting messy source documents into a canonical schema, and (2) writing
the final narrative from already-computed findings.

## Architecture

```
Intake (LLM extract + reconciliation gate)
  → Analysis (pandas, pure deterministic)
    → Benchmark (peer comparison + rule flags)
      → Strategy (LLM proposes actions, code computes projections)
        → Briefing (LLM narrates, grounding gate verifies)
```

## Setup

### Prerequisites
- Python 3.11+
- Node.js 20+

### Backend

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env
# Edit .env with your OpenRouter API key
```

### Frontend

```bash
cd frontend
npm install
```

### Run

```bash
# Terminal 1 — backend
cd backend
uvicorn api.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

Open http://localhost:5173. Upload a financial statement (or use the included sample).

## Configuration

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | — | Required for LLM stages |
| `MODEL_NAME` | `meta-llama/llama-3.1-8b-instruct:free` | Primary LLM |
| `FALLBACK_MODEL` | `mistralai/mistral-7b-instruct:free` | Used on primary failure |
| `DATA_MODE` | `test` | `test` allows free models; `real` blocks them |

## Running tests (no API key needed)

```bash
cd backend
python -m pytest tests/ -v
```

## Sample data

`data/samples/mustermann_gmbh.json` — Mustermann Metallbau GmbH, a fictional
German Mittelstand manufacturer with 3 years of HGB financials. Demonstrates:
- Declining EBIT margin trend (22% → 20% → 18%)
- Elevated DSO (~78 days vs 48-day sector median)
- No cash flow statement (typical for HGB GmbH — handled gracefully)

## Benchmark data

`data/benchmarks/` — Industry peer medians and quartiles (p25/p75) from
Bundesbank/ECB BACH database, used for flag rules and projection scenario bounds.

## Projection scenarios

Scenarios are bounded by peer benchmark quartiles, not arbitrary multipliers:
- **Optimistic**: improve to peer p75 (top quartile)
- **Base**: improve to peer median
- **Conservative**: improve halfway to peer median

Every assumption is surfaced verbatim in the output.
All projections are clearly labeled "projection, not a guarantee."

## Project structure

```
backend/
  schema/          Pydantic canonical schema
  analysis/        Deterministic ratio engine + reconciliation gate
  benchmark/       Peer store + rule-based flags
  llm/             OpenRouter abstraction (Steps 3+)
  intake/          PDF/Excel/CSV parsers + LLM extraction (Steps 3+)
  strategy/        Typed actions + projection engine (Step 4+)
  briefing/        Narrative generation + grounding gate (Steps 3+)
  pipeline/        Orchestrator + WebSocket events (Step 5+)
  api/             FastAPI app (Step 5+)
  tests/
frontend/          React + R3F 3D visualization (Step 6+)
data/
  samples/         Fictional German company datasets
  benchmarks/      Sector peer benchmarks (NACE)
```
