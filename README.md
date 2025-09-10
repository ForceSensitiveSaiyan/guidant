Guidant — RAG app (FastAPI + Streamlit + Chroma + OpenAI)

Guidant is a Retrieval-Augmented Generation (RAG) app for social workers.
It uses a local Chroma vector DB (built from your PDFs/TXTs) and an OpenAI chat model for responses.
UI is Streamlit; API is FastAPI. In production, Caddy provides HTTPS and reverse proxying.

Table of contents

Features

Repository layout

Requirements

Configuration

Local development (Windows & Mac/Linux)

VPS + Docker deployment

Routine operations

Troubleshooting

Quality & CI (optional)

Security notes

License

Features

🔎 Local embeddings with sentence-transformers + Chroma (persisted on disk)

💬 Generation via OpenAI (fast, reliable)

🖥️ Streamlit UI, FastAPI backend

🔐 Caddy TLS + reverse proxy (prod)

🧩 Docs live in ./docs (versionable), index in ./chroma_db (generated)

Repository layout
guidant/
  api.py
  rag.py
  populate_db.py
  ui.py
  assets/                 # logos, images
  docs/                   # source PDFs/TXTs (your corpus)
  chroma_db/              # generated index (do NOT commit)
  cloud-deploy/
    Dockerfile.api
    Dockerfile.ui
    docker-compose.yml
    Caddyfile
    .env.example
    requirements.api.txt  # prod deps (API only)
    requirements.dev.txt  # dev deps (API + UI)
  .gitignore
  .dockerignore
  README.md


Tip: If your PDFs are large, consider Git LFS for docs/.

Requirements

Python 3.11

(For local dev UI) modern browser

(For VPS) Docker Engine + Docker Compose plugin

OpenAI API key

Configuration

Copy the example and set real values (never commit secrets):

cloud-deploy/.env.example

# Public site (use YOUR-IP.sslip.io or real domain)
DOMAIN=157.180.81.235.sslip.io
EMAIL=you@example.com
API_UPSTREAM=api:8000

# UI → API inside Docker network
PUBLIC_API_URL=http://api:8000
REQUEST_TIMEOUT=600

# LLM
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini
# OPENAI_API_KEY goes only in .env (not here)


Create your actual .env:

cp cloud-deploy/.env.example cloud-deploy/.env
# then edit and add: OPENAI_API_KEY=sk-...

Local development (Windows & Mac/Linux)

Uses your local Python (no Docker). Easiest for iterating on code.

1) Create & activate a virtual environment

Windows (PowerShell)

cd <path-to-your-cloned-repo>
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # if blocked: Set-ExecutionPolicy -Scope Process RemoteSigned


Mac/Linux

cd <path-to-your-cloned-repo>
python3 -m venv .venv
source .venv/bin/activate

2) Install dev dependencies (API + UI)
python -m pip install -U pip wheel setuptools
pip install -r cloud-deploy/requirements.dev.txt

3) Provide configuration
# already copied above, then edit and add your real key:
# cloud-deploy/.env  → OPENAI_API_KEY=sk-...


If you already have a prebuilt index locally, place it in ./chroma_db.
Otherwise, put PDFs/TXTs into ./docs and build the index (can take time):

python populate_db.py

4) Run API and UI (two terminals, same venv)

Terminal A — API

# Windows PowerShell:
$env:OPENAI_API_KEY = (Select-String -Path cloud-deploy\.env -Pattern '^OPENAI_API_KEY=').ToString().Split('=')[1].Trim()
$env:LLM_PROVIDER   = 'openai'
$env:OPENAI_MODEL   = 'gpt-4o-mini'
python -m uvicorn api:app --reload --port 8000

# Mac/Linux:
export $(grep -v '^\s*#' cloud-deploy/.env | xargs)
export LLM_PROVIDER=openai
export OPENAI_MODEL=${OPENAI_MODEL:-gpt-4o-mini}
python -m uvicorn api:app --reload --port 8000


Terminal B — UI

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
$env:API_URL = 'http://localhost:8000'
$env:REQUEST_TIMEOUT = '600'
python -m streamlit run ui.py

# Mac/Linux:
source .venv/bin/activate
export API_URL='http://localhost:8000'
export REQUEST_TIMEOUT=600
python -m streamlit run ui.py


Open: http://localhost:8501

VPS + Docker deployment

Assumes Ubuntu VPS (Hetzner), Docker + Compose installed.

0) One-time server prep (optional but recommended)
# Firewall
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
sudo ufw --force enable

# Swap (helps Python builds; harmless with our slim images)
sudo fallocate -l 8G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

1) Clone code onto the server
sudo mkdir -p /opt/guidant && sudo chown -R $USER:$USER /opt/guidant
cd /opt/guidant
git clone https://github.com/YOUR_USER/guidant.git .  # or SSH

2) Prepare data folders
mkdir -p docs chroma_db   # mount into the API container
# copy your PDFs/TXTs into /opt/guidant/docs

3) Configure env for deploy
cd /opt/guidant/cloud-deploy
cp .env.example .env
nano .env  # set DOMAIN, EMAIL, OPENAI_API_KEY, etc.


Tip: Use YOUR-IP.sslip.io as DOMAIN for instant TLS via Let’s Encrypt.

4) Build & start
cd /opt/guidant/cloud-deploy
docker compose up -d --build
docker compose ps

5) Index the documents
docker compose exec api python /app/populate_db.py
docker compose exec -T api python - <<'PY'
import chromadb; c=chromadb.PersistentClient(path='./chroma_db').get_collection('langchain'); print('count =', c.count())
PY

6) Validate
curl -s https://$DOMAIN/health
curl -s https://$DOMAIN/api/ask \
  -H 'content-type: application/json' \
  -d '{"question":"Give me a brief overview of the Children Act in my docs."}'


Open: https://$DOMAIN

Routine operations
# Pull new code & redeploy
cd /opt/guidant && git pull
cd cloud-deploy && docker compose up -d --build

# Reindex after changing /opt/guidant/docs
docker compose exec api python /app/populate_db.py

# Logs
docker compose logs -f --tail=200 api
docker compose logs -f --tail=200 ui
docker compose logs -f --tail=200 caddy

# Restart services
docker compose restart api
docker compose restart ui
docker compose restart caddy

Troubleshooting

UI shows “API request failed”

API not running, or env not set. Check docker compose logs api.

Ensure OPENAI_API_KEY is set in cloud-deploy/.env and no empty OPENAI_BASE_URL/OPENAI_API_VERSION lines.

“Couldn’t find anything relevant”

Index likely empty. Run populate_db.py and confirm count > 0.

Caddy shows cert/parse errors

docker compose logs caddy

Use a valid DOMAIN that resolves to your VPS IP (sslip.io works instantly).

Local dev: ‘streamlit’ not recognized

Activate venv and use python -m streamlit run ui.py.

Quality & CI (optional)

Pre-commit (format + lint locally)

pip install pre-commit
cat > .pre-commit-config.yaml <<'EOF'
repos:
  - repo: https://github.com/psf/black
    rev: 24.8.0
    hooks: [ { id: black, language_version: python3.11 } ]
  - repo: https://github.com/pycqa/flake8
    rev: 7.1.0
    hooks: [ { id: flake8, additional_dependencies: [flake8-bugbear==24.4.26] } ]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
EOF
pre-commit install


Minimal CI (GitHub Actions)

# .github/workflows/ci.yml
name: CI (lint)
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: |
          python -m pip install --upgrade pip
          pip install black==24.8.0 flake8==7.1.0 flake8-bugbear==24.4.26
      - run: black --check .
      - run: flake8 .

Security notes

Secrets only in cloud-deploy/.env (never in git).

Consider basic auth in Caddy for test environments.

Be cautious with PII in logs; log minimal request details.

License

Choose a license (e.g., MIT) that fits your use case. Example:

MIT License – © YOUR_NAME, YEAR
