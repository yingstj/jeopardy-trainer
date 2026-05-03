# Jayopardy!

A Streamlit-based Jeopardy quiz app with Google sign-in, guest play, and category analysis.

## Stack
- Python 3.12
- Streamlit (frontend)
- SQLite (local DB via `database.py`)
- Optional Cloudflare R2 for dataset storage
- sentence-transformers + scikit-learn for category similarity

## Entry point
- `app.py` — main Streamlit app

## Run
- Workflow `Start application`: `streamlit run app.py --server.port 5000 --server.address 0.0.0.0`
- Streamlit config in `.streamlit/config.toml` binds `0.0.0.0:5000`, disables CORS/XSRF for the Replit iframe proxy.

## Deployment
- Reserved VM (single always-on instance, required because user/challenge/bookmark state lives in local SQLite `jeopardy_trainer.db`).
- Run command: `streamlit run app.py --server.port 5000 --server.address 0.0.0.0`

## Secrets
- Optional `.streamlit/secrets.toml` for Google OAuth + R2 credentials (see `SECRETS_SETUP.md`).
