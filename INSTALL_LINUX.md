# Kodrlytics — Linux Server Installation Guide

Covers **Ubuntu 22.04 / 24.04 LTS** and **Debian 12**. Commands are identical for both unless noted. Assumes a clean server with `sudo` access.

---

## 1. System Prerequisites

### 1.1 Update package index

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Install system packages

```bash
sudo apt install -y \
  git \
  curl \
  build-essential \
  libssl-dev \
  libffi-dev \
  zlib1g-dev \
  libbz2-dev \
  libreadline-dev \
  libsqlite3-dev \
  libncursesw5-dev \
  xz-utils \
  tk-dev \
  libxml2-dev \
  libxmlsec1-dev \
  liblzma-dev \
  ca-certificates \
  gnupg
```

### 1.3 Python 3.11

**Ubuntu 22.04** — add the deadsnakes PPA:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

**Ubuntu 24.04** — Python 3.11 is in the default repos:

```bash
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

**Debian 12** — backports already includes 3.11:

```bash
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

Verify:

```bash
python3.11 --version
# Expected: Python 3.11.x
```

### 1.4 Node.js 20 (via NodeSource)

Do not use the distro's default Node — it is usually too old.

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

Verify:

```bash
node --version   # Expected: v20.x.x
npm --version    # Expected: 10.x.x
```

---

## 2. Clone the Repository

```bash
git clone https://github.com/kodrprod/kodrlytics.git
cd kodrlytics
```

If you are deploying to a server without direct GitHub access, clone on your local machine first and then `rsync` or `scp` the directory across — or use a deploy key.

---

## 3. Backend Setup

### 3.1 Create a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Your prompt will now show `(.venv)`. To activate in future sessions:

```bash
source /path/to/kodrlytics/.venv/bin/activate
```

### 3.2 Install Python dependencies

```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

Verify:

```bash
python -c "import fastapi, pandas, pdfplumber; print('Backend deps OK')"
# Expected: Backend deps OK
```

### 3.3 Configure environment variables

```bash
cp .env.example .env
nano .env   # or vim, or any editor
```

Fill in your values:

```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
MODEL_NAME=google/gemma-4-31b-it:free
FALLBACK_MODEL=google/gemma-4-26b-a4b-it:free
DATA_MODE=test
```

**Getting an OpenRouter API key:**
1. Go to [https://openrouter.ai/keys](https://openrouter.ai/keys)
2. Sign up / log in → click **Create Key**
3. Copy the key (starts with `sk-or-v1-`) into `.env`

> **DATA_MODE:**
> - `test` — free models allowed, LLM responses cached in `dev.db` to save quota
> - `real` — free models **blocked**. Use this for real client data to prevent it being processed by providers who may log free-tier requests.

### 3.4 Verify the backend imports

```bash
python -c "from backend.api.main import app; print('API import OK')"
# Expected: API import OK
```

### 3.5 Run the test suite (no API key needed)

```bash
python -m pytest backend/tests/ -v
```

Expected: **44 passed** in under 2 seconds. No LLM calls are made.

---

## 4. Frontend Setup

### 4.1 Install Node dependencies

```bash
cd frontend
npm install
cd ..
```

### 4.2 Verify TypeScript compiles

```bash
cd frontend && npx tsc --noEmit && cd ..
# Expected: no output (zero errors)
```

---

## 5. Running the Application

### Development mode (two terminals)

**Terminal 1 — Backend:**

```bash
cd /path/to/kodrlytics
source .venv/bin/activate
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

> Use `--host 0.0.0.0` to accept connections from other machines on the network (e.g. your laptop hitting a remote dev server). For localhost-only, omit it.

**Terminal 2 — Frontend:**

```bash
cd /path/to/kodrlytics/frontend
npm run dev -- --host 0.0.0.0
```

> The `--host 0.0.0.0` flag makes Vite accessible from outside the server. Omit it for localhost-only.

Open **http://your-server-ip:5173** in a browser. Click **RUN SAMPLE** to start the demo.

---

## 6. Production Deployment (systemd + nginx)

For a persistent, production-grade setup: the backend runs as a systemd service behind nginx, and the frontend is served as a static build.

### 6.1 Build the frontend

```bash
cd /path/to/kodrlytics/frontend
npm run build
# Output goes to frontend/dist/
```

### 6.2 Create a systemd service for the backend

Create the service file:

```bash
sudo nano /etc/systemd/system/kodrlytics.service
```

Paste (adjust paths and user to match your setup):

```ini
[Unit]
Description=Kodrlytics Financial Analysis API
After=network.target

[Service]
Type=exec
User=ubuntu
WorkingDirectory=/home/ubuntu/kodrlytics
Environment="PATH=/home/ubuntu/kodrlytics/.venv/bin:/usr/bin:/bin"
EnvironmentFile=/home/ubuntu/kodrlytics/.env
ExecStart=/home/ubuntu/kodrlytics/.venv/bin/uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kodrlytics
sudo systemctl start kodrlytics
sudo systemctl status kodrlytics
```

Check logs:

```bash
sudo journalctl -u kodrlytics -f
```

### 6.3 Install and configure nginx

```bash
sudo apt install -y nginx
```

Create a site config:

```bash
sudo nano /etc/nginx/sites-available/kodrlytics
```

Paste (replace `your-domain.com` with your actual domain or server IP):

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend — serve the Vite build
    root /home/ubuntu/kodrlytics/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API — proxy to uvicorn
    location /runs {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 25M;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
    }

    # WebSocket endpoint
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 300s;
    }
}
```

Enable and test:

```bash
sudo ln -s /etc/nginx/sites-available/kodrlytics /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6.4 Update the frontend WebSocket URL for production

By default the frontend connects to `ws://localhost:8000`. For a deployed server, update the URL in the hook before building:

```bash
nano frontend/src/hooks/usePipelineWS.ts
```

Change:
```ts
const BACKEND = 'http://localhost:8000'
const WS_BACKEND = 'ws://localhost:8000'
```
To (use `wss://` if you have TLS):
```ts
const BACKEND = ''           // empty = same origin (nginx proxies it)
const WS_BACKEND = 'ws://your-domain.com'
```

Then rebuild:

```bash
cd frontend && npm run build
```

### 6.5 HTTPS with Let's Encrypt (recommended)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

Certbot will automatically update the nginx config. After this, change `WS_BACKEND` to `wss://your-domain.com` and rebuild the frontend.

Auto-renewal is configured automatically. Test it:

```bash
sudo certbot renew --dry-run
```

---

## 7. Running the CLI Demo (Optional)

To test the full pipeline from the command line without a browser:

```bash
source .venv/bin/activate
python backend/pipeline/demo_runner.py
```

Prints all 5 stages with findings, flags, projections, and the narrative. Useful for verifying the API key works before opening a browser.

---

## 8. Firewall Configuration

If you are using `ufw`:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'   # HTTP (80) + HTTPS (443)
sudo ufw enable
sudo ufw status
```

If running in development only (no nginx), allow ports directly:

```bash
sudo ufw allow 8000   # backend
sudo ufw allow 5173   # frontend dev server
```

---

## 9. Troubleshooting

### `python3.11: command not found`

The deadsnakes PPA install may not have linked the binary. Check:

```bash
ls /usr/bin/python3*
```

If `python3.11` is there, use it explicitly. Or create a symlink:

```bash
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

### `ModuleNotFoundError: No module named 'backend'`

You are running Python from inside the `backend/` directory. Always run from the project root:

```bash
cd /path/to/kodrlytics   # repo root
python -m pytest backend/tests/ -v
```

### Virtual environment not active

```bash
source /path/to/kodrlytics/.venv/bin/activate
```

### `npm install` fails with permissions error

Never run `npm` as root. If you accidentally did:

```bash
sudo chown -R $(whoami) ~/.npm
sudo chown -R $(whoami) /path/to/kodrlytics/frontend/node_modules
```

### OpenRouter returns 404 on model

The free model in `.env` is no longer available on OpenRouter's network. Find a working one:

```bash
python -c "
import httpx, os
from dotenv import load_dotenv; load_dotenv()
r = httpx.get('https://openrouter.ai/api/v1/models',
    headers={'Authorization': f'Bearer {os.environ[\"OPENROUTER_API_KEY\"]}'})
models = [m['id'] for m in r.json()['data'] if ':free' in m['id']]
print('\n'.join(models))
"
```

Update `MODEL_NAME` in `.env`, then restart the service:

```bash
sudo systemctl restart kodrlytics
```

### OpenRouter 429 rate limits

The free tier allows ~20 requests/minute. The router retries automatically with backoff (2 → 4 → 8 → 16 seconds). The LLM response cache in `dev.db` (when `DATA_MODE=test`) means repeated runs on the same document skip the API call entirely. For production throughput, use a paid model.

### WebSocket connection refused in browser

Confirm the backend is running and listening on the right interface:

```bash
ss -tlnp | grep 8000
```

If behind nginx, confirm the `location /ws/` block is in the nginx config and nginx has been reloaded.

### Port already in use

```bash
# Find and kill the process on port 8000
sudo ss -tlnp | grep ':8000'
sudo kill -9 <PID>
```

### systemd service fails to start

Check the journal for the exact error:

```bash
sudo journalctl -u kodrlytics --since "5 minutes ago"
```

Common causes:
- Wrong `WorkingDirectory` path
- `.env` file not found (check `EnvironmentFile` path)
- Python not found in `PATH` inside the unit

---

## 10. Keeping Dependencies Up to Date

When OpenRouter deprecates a free model, update `.env`:

```bash
nano .env
# Change MODEL_NAME and FALLBACK_MODEL to currently available free models
sudo systemctl restart kodrlytics   # if running as a service
```

To update Python packages:

```bash
source .venv/bin/activate
pip install --upgrade -r backend/requirements.txt
sudo systemctl restart kodrlytics
```

To update Node packages:

```bash
cd frontend
npm update
npm run build
```

---

## 11. Directory Reference

```
kodrlytics/
├── .env                    ← Your secrets (gitignored — never commit)
├── .env.example            ← Template — copy to .env
├── .venv/                  ← Python virtual environment (gitignored)
├── dev.db                  ← LLM response cache in DATA_MODE=test (gitignored)
├── backend/
│   ├── api/main.py         ← FastAPI app (POST /runs, WS /ws/{run_id})
│   ├── pipeline/           ← Orchestrator + WebSocket event models
│   ├── schema/models.py    ← Canonical financial schema (Pydantic)
│   ├── analysis/           ← Deterministic ratio engine (pandas, ~22 ratios)
│   ├── benchmark/          ← Peer store + rule-based flags
│   ├── intake/             ← Document parsers + LLM extraction
│   ├── strategy/           ← Typed actions + projection engine
│   ├── briefing/           ← Narrative generation + grounding gate
│   ├── llm/router.py       ← OpenRouter abstraction layer
│   ├── tests/              ← 44 unit + integration tests
│   └── requirements.txt
├── frontend/
│   ├── dist/               ← Production build output (after npm run build)
│   └── src/
│       ├── scene/          ← R3F 3D scene (hubs, packets, labels, beams)
│       ├── hud/            ← HUD overlay (event log, results panel)
│       └── hooks/          ← WebSocket state management
└── data/
    ├── samples/            ← mustermann_gmbh.json (demo company)
    └── benchmarks/         ← NACE sector peer medians (Bundesbank/BACH)
```
