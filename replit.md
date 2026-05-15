# Jayopardy!

A Streamlit-based Jeopardy quiz app with Google sign-in, guest play, and category analysis.

## Stack
- Python 3.12
- Streamlit (frontend)
- Postgres (Replit managed; `DATABASE_URL` env var) via `database.py`
  - `database.py` exposes a sqlite3-compatible shim (`?` placeholders,
    `INSERT OR IGNORE`, `cursor.lastrowid`) backed by psycopg2 so the rest of
    the app doesn't need to know about Postgres.
- Optional Cloudflare R2 for dataset storage
- sentence-transformers + scikit-learn for category similarity

## Entry point
- `app.py` — main Streamlit app

## Run
- Workflow `Start application`: `streamlit run app.py --server.port 5000 --server.address 0.0.0.0`
- Streamlit config in `.streamlit/config.toml` binds `0.0.0.0:5000`, disables CORS/XSRF for the Replit iframe proxy.

## Deployment
- Autoscale deployment (recommended). All durable state lives in managed
  Postgres, so the deployment container is stateless and can spin up fresh
  per request — no sticky-disk failures, no single point of failure.
- Run command: `streamlit run app.py --server.port 5000 --server.address 0.0.0.0`
- Previously ran on Reserved VM with local SQLite (`jeopardy_trainer.db`).
  Migrated to Postgres on May 14 2026 after a Reserved VM volume hit
  `OSError: [Errno 5] Input/output error` reading `.pythonlibs`. The legacy
  `jeopardy_trainer.db` file is left in the repo for reference only — it is
  no longer read or written by the app.

## Secrets
- Optional `.streamlit/secrets.toml` for Google OAuth + R2 credentials (see `SECRETS_SETUP.md`).
