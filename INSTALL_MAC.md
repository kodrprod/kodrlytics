# Kodrlytics — macOS Installation Guide

Tested on macOS 13 Ventura and macOS 14 Sonoma (Intel and Apple Silicon).

---

## 1. Prerequisites

### 1.1 Xcode Command Line Tools

Required for git and compiler tooling.

```bash
xcode-select --install
```

A dialog will appear. Click **Install** and wait for it to finish (~5 min). Verify:

```bash
xcode-select -p
# Expected: /Library/Developer/CommandLineTools
```

### 1.2 Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After install, follow the **"Next steps"** instructions Homebrew prints — on Apple Silicon you must add Homebrew to your PATH:

```bash
# Apple Silicon only (M1/M2/M3/M4)
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Verify:

```bash
brew --version
# Expected: Homebrew 4.x.x
```

### 1.3 Python 3.11+

macOS ships an outdated Python. Install a current version via Homebrew:

```bash
brew install python@3.11
```

Add it to your PATH (add to `~/.zprofile` or `~/.bash_profile`):

```bash
echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile
```

Verify:

```bash
python3.11 --version
# Expected: Python 3.11.x
```

### 1.4 Node.js 20+

```bash
brew install node@20
```

Add to PATH (Apple Silicon path shown — Intel uses `/usr/local`):

```bash
echo 'export PATH="/opt/homebrew/opt/node@20/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile
```

Verify:

```bash
node --version   # Expected: v20.x.x
npm --version    # Expected: 10.x.x
```

### 1.5 Git

Git is included with Xcode Command Line Tools. Verify:

```bash
git --version
# Expected: git version 2.x.x
```

---

## 2. Clone the Repository

```bash
git clone https://github.com/kodrprod/kodrlytics.git
cd kodrlytics
```

---

## 3. Backend Setup

### 3.1 Create a virtual environment

Using a virtual environment keeps project dependencies isolated from your system Python.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Your prompt will now show `(.venv)`. You must activate the venv in every new terminal session:

```bash
source .venv/bin/activate
```

### 3.2 Install Python dependencies

```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

This installs: FastAPI, uvicorn, pandas, numpy, pdfplumber, openpyxl, httpx, pydantic, and test tooling.

Verify the key packages:

```bash
python -c "import fastapi, pandas, pdfplumber; print('Backend deps OK')"
# Expected: Backend deps OK
```

### 3.3 Configure environment variables

```bash
cp .env.example .env
```

Open `.env` in any editor and fill in your values:

```bash
nano .env
```

```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
MODEL_NAME=google/gemma-4-31b-it:free
FALLBACK_MODEL=google/gemma-4-26b-a4b-it:free
DATA_MODE=test
```

**Getting an OpenRouter API key:**
1. Go to [https://openrouter.ai/keys](https://openrouter.ai/keys)
2. Sign up / log in
3. Click **Create Key**
4. Copy the key (starts with `sk-or-v1-`) into `.env`

> **Note on DATA_MODE:**
> - `test` — free models are allowed, responses are cached locally in `dev.db` to save API calls
> - `real` — free models are **blocked**. Required when analysing real client data to prevent it being sent to providers who may log or train on free-tier requests.

### 3.4 Verify the backend can import correctly

```bash
python -c "from backend.api.main import app; print('API import OK')"
# Expected: API import OK
```

### 3.5 Run the test suite (no API key needed)

The deterministic core is fully testable without any LLM calls:

```bash
python -m pytest backend/tests/ -v
```

Expected output: **44 passed** in under 2 seconds.

---

## 4. Frontend Setup

### 4.1 Install Node dependencies

```bash
cd frontend
npm install
cd ..
```

This installs React 18, React Three Fiber, three.js, Vite, and TypeScript tooling (~350 MB in `node_modules`).

### 4.2 Verify TypeScript compiles

```bash
cd frontend
npx tsc --noEmit
cd ..
# Expected: no output (zero errors)
```

---

## 5. Running the Application

You need **two terminal windows** open simultaneously.

### Terminal 1 — Backend API server

```bash
cd /path/to/kodrlytics
source .venv/bin/activate
uvicorn backend.api.main:app --reload --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

### Terminal 2 — Frontend dev server

```bash
cd /path/to/kodrlytics/frontend
npm run dev
```

Expected output:
```
  VITE v5.x.x  ready in 264ms
  ➜  Local:   http://localhost:5173/
```

### Open the application

Navigate to **[http://localhost:5173](http://localhost:5173)** in your browser.

You should see a dark 3D space with five glowing hub nodes. Click **RUN SAMPLE** in the right panel to start a demo analysis on the included fictional company (Mustermann Metallbau GmbH). The hubs will animate live as the pipeline runs.

---

## 6. Running the CLI Demo (Optional)

To test the full pipeline from the command line without the browser:

```bash
source .venv/bin/activate
python backend/pipeline/demo_runner.py
```

This runs the 5-stage pipeline on the sample company and prints all events to the terminal, including findings, flags, projections, and the LLM-generated narrative.

---

## 7. Uploading Your Own Financial Statements

The **UPLOAD FILE** button in the HUD accepts:

| Format | Notes |
|--------|-------|
| `.csv` | Single company, any delimiter |
| `.xlsx` | All sheets are parsed |
| `.pdf` | Text-based PDFs (scanned/image PDFs are not supported) |

The LLM extraction stage handles messy, non-standard layouts. If reconciliation fails (the accounting identities don't balance), the system re-extracts once automatically before rejecting.

For real financial data, set `DATA_MODE=real` in `.env` and use a paid model with a no-logging policy (e.g. `anthropic/claude-3-5-sonnet` on OpenRouter with the `no-log` flag enabled).

---

## 8. Troubleshooting

### `command not found: python3.11`

The Homebrew Python is not on your PATH. Run:

```bash
echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile
```

On Intel Macs, replace `/opt/homebrew` with `/usr/local`.

### `ModuleNotFoundError: No module named 'backend'`

You are running Python outside the repo root. Always run commands from the `kodrlytics/` directory, not from inside `backend/`:

```bash
cd /path/to/kodrlytics
python -m pytest backend/tests/ -v   # correct
```

### `(.venv) not active` — imports fail

Re-activate the virtual environment:

```bash
source .venv/bin/activate
```

### OpenRouter returns 404

The free model in your `.env` is no longer available. Check which free models are currently live:

```bash
python -c "
import httpx, os
from dotenv import load_dotenv; load_dotenv()
r = httpx.get('https://openrouter.ai/api/v1/models', headers={'Authorization': f'Bearer {os.environ[\"OPENROUTER_API_KEY\"]}'})
models = [m['id'] for m in r.json()['data'] if ':free' in m['id']]
print('\n'.join(models))
"
```

Pick one and update `MODEL_NAME` in `.env`.

### OpenRouter returns 429 (rate limit)

The free tier allows ~20 requests/minute. The router retries automatically with exponential backoff (2s → 4s → 8s → 16s). If all retries exhaust, wait 1 minute and try again. Upgrade to a paid model for production use.

### Frontend: `npm install` fails with EACCES permission errors

Never run `npm install` with `sudo`. Fix npm's permissions:

```bash
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile
```

Then re-run `npm install` inside `frontend/`.

### Port 8000 already in use

```bash
lsof -ti:8000 | xargs kill -9
```

### Port 5173 already in use

```bash
lsof -ti:5173 | xargs kill -9
```

---

## 9. Directory Reference

```
kodrlytics/
├── .env                    ← Your secrets (gitignored — never commit)
├── .env.example            ← Template — copy to .env
├── .venv/                  ← Python virtual environment (gitignored)
├── dev.db                  ← LLM response cache in DATA_MODE=test (gitignored)
├── backend/
│   ├── api/main.py         ← FastAPI app (POST /runs, WS /ws/{run_id})
│   ├── pipeline/           ← Orchestrator + event models
│   ├── schema/models.py    ← Canonical financial schema (Pydantic)
│   ├── analysis/           ← Deterministic ratio engine (pandas)
│   ├── benchmark/          ← Peer store + rule-based flags
│   ├── intake/             ← Document parsers + LLM extraction
│   ├── strategy/           ← Typed actions + projection engine
│   ├── briefing/           ← Narrative generation + grounding gate
│   ├── llm/router.py       ← OpenRouter abstraction layer
│   ├── tests/              ← 44 unit + integration tests
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── scene/          ← R3F 3D scene (hubs, packets, labels)
│       ├── hud/            ← Overlay panel (event log, results)
│       └── hooks/          ← WebSocket state management
└── data/
    ├── samples/            ← mustermann_gmbh.json (demo company)
    └── benchmarks/         ← NACE sector peer medians (Bundesbank/BACH)
```
