# Jay's Jeopardy Trainer

A Streamlit app that helps you practice Jeopardy questions using a large dataset (Cloudflare R2 if configured, otherwise a public GitHub fallback).

## Features

- Train with a large collection of real Jeopardy clues and responses
- Filter by category
- Adjustable time limits
- Track your progress within each session
- Semantic suggestions after incorrect answers to find related clues
- Adaptive retry mode to focus on clues you've missed
- Optional AI opponent (buzz-in and difficulty settings)
- Bookmarks and notes

## How It Works

1. The app loads Jeopardy clues from Cloudflare R2 using S3-compatible APIs when Streamlit secrets are set; otherwise it falls back to a public GitHub dataset.
2. You can filter by categories you're interested in
3. The app presents clues and you try to answer them within the time limit
4. Your progress is tracked throughout your session
5. For incorrect answers, the app suggests similar clues to help you learn

## Deployment

This app is designed to be deployed on Streamlit Cloud, which provides free hosting for Streamlit apps.

### Environment Variables

To enable Cloudflare R2 loading, set these Streamlit secrets (otherwise the app will use the public GitHub dataset):

- `R2_ENDPOINT_URL`: Your Cloudflare R2 endpoint URL
- `R2_ACCESS_KEY`: Your R2 access key
- `R2_SECRET_KEY`: Your R2 secret key
- `R2_BUCKET_NAME`: Your R2 bucket name (default: jeopardy-dataset)
- `R2_FILE_KEY`: The name of your dataset file (default: all_jeopardy_clues.csv)

### Authentication

- The main app (`app.py`) uses a simple username/password flow backed by a local JSON file via `UserManager` to persist session stats and bookmarks.
- An alternative email/Google OAuth flow exists in `auth_manager.py` and `test_auth.py` but is not wired into `app.py` by default. See `AUTH_SETUP.md` if you want to enable OAuth in deployment.

#### Google OAuth (optional)

Quick setup:

1. Create OAuth credentials in Google Cloud (Web Application), add authorized redirect URIs:
   - Local: `http://localhost:8501`
   - Streamlit Cloud: `https://your-app.streamlit.app`
2. Add secrets (Streamlit Cloud Secrets or local `.streamlit/secrets.toml`):

   ```toml
   GOOGLE_CLIENT_ID = "your-client-id.apps.googleusercontent.com"
   GOOGLE_CLIENT_SECRET = "your-client-secret"
   # For local dev:
   REDIRECT_URI = "http://localhost:8501"
   # For Streamlit Cloud (optional override):
   # REDIRECT_URI = "https://your-app.streamlit.app"
   ```

3. On the login screen, use the “🔐 Google Sign-In” tab or the sidebar button “Continue with Google”.

## Local Development

1. Clone the repository:

   ```bash
   git clone https://github.com/yingstj/jeopardy-trainer.git
   cd jeopardy-trainer
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up secrets (optional, only needed for R2; otherwise GitHub fallback is used):

   ```bash
   # Option 1: Environment variables
   export R2_ENDPOINT_URL="your-r2-endpoint"
   export R2_ACCESS_KEY="your-access-key"
   export R2_SECRET_KEY="your-secret-key"
   
   # Option 2: Create .streamlit/secrets.toml (not tracked in git)
   ```

4. Run the app:

   ```bash
   streamlit run app.py
   ```

## Files

- `app.py` - Main Streamlit application
- `r2_jeopardy_data_loader.py` - Loads data from Cloudflare R2 (with GitHub fallback)
- `semantic_explorer.py` - Tool for exploring semantically similar clues
- `requirements.txt` - Dependencies for deployment
