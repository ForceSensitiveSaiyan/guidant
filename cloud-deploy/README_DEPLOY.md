# Cloud Deploy (VPS + Docker + Caddy)

This folder lets you run your FastAPI + Streamlit app behind HTTPS on a single VPS.

## What it includes
- `docker-compose.yml` – orchestrates api/ui/caddy
- `Dockerfile.api` + `requirements.api.txt` – FastAPI container
- `Dockerfile.ui`  + `requirements.ui.txt` – Streamlit container
- `Caddyfile` – HTTPS reverse proxy
- `.env.example` – domain/email/API settings

## Quick Start
1) Copy this `cloud-deploy` folder into `~/app/` on your server.
2) In your code:
   - **ui.py**: use env var for API URL
     ```python
     import os
     API_URL = os.getenv("API_URL", "http://localhost:8000")
     response = requests.post(f"{API_URL}/ask", json={"question": question}, timeout=120)
     ```
   - **api.py**: enable CORS
     ```python
     from fastapi.middleware.cors import CORSMiddleware
     app.add_middleware(
         CORSMiddleware,
         allow_origins=["*"],
         allow_credentials=True,
         allow_methods=["*"],
         allow_headers=["*"],
     )
     ```
3) Configure:
   ```bash
   cd ~/app/cloud-deploy
   cp .env.example .env
   nano .env   # set DOMAIN, EMAIL; API_UPSTREAM can stay api:8000
   ```
4) Run:
   ```bash
   docker compose up -d --build
   docker compose exec api python populate_db.py
   ```
5) Open `https://YOUR_DOMAIN` (or `https://YOUR.SERVER.IP.sslip.io`).

Tips: Logs with `docker compose logs -f caddy|api|ui`.
