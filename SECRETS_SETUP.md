# Secrets Configuration

This app requires external service credentials to function fully. For security, these are **not** stored in the repository.

## Environment Variables

Set these environment variables before running the app:

### Cloudflare R2 (for dataset storage)
```bash
export R2_ENDPOINT_URL="https://your-account-id.r2.cloudflarestorage.com"
export R2_ACCESS_KEY="your-r2-access-key"
export R2_SECRET_KEY="your-r2-secret-key"
export R2_BUCKET_NAME="jeopardy-dataset"
export R2_FILE_KEY="all_jeopardy_clues.csv"
```

### Google OAuth (optional, for social login)
```bash
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"
export REDIRECT_URI="https://your-app-url.streamlit.app/"
export OAUTH_COMPONENT_REDIRECT_URI="https://share.streamlit.io/component/streamlit_oauth.authorize_button/index.html"
```

## Streamlit Cloud Deployment

When deploying to Streamlit Cloud:

1. Go to your app settings
2. Add the above variables in the "Secrets" section using TOML format:

```toml
R2_ENDPOINT_URL = "https://your-account-id.r2.cloudflarestorage.com"
R2_ACCESS_KEY = "your-r2-access-key"
R2_SECRET_KEY = "your-r2-secret-key"
R2_BUCKET_NAME = "jeopardy-dataset"
R2_FILE_KEY = "all_jeopardy_clues.csv"

GOOGLE_CLIENT_ID = "your-google-client-id"
GOOGLE_CLIENT_SECRET = "your-google-client-secret"
REDIRECT_URI = "https://your-app-url.streamlit.app/"
OAUTH_COMPONENT_REDIRECT_URI = "https://share.streamlit.io/component/streamlit_oauth.authorize_button/index.html"
```

## Local Development

For local development, you can either:

1. Set environment variables as shown above, or
2. Create a local `.streamlit/secrets.toml` file (not tracked in git) with the TOML format above

## Fallback Behavior

- If R2 credentials are missing, the app falls back to loading data from GitHub
- If Google OAuth is not configured, users can still create local accounts
- The app will display appropriate warnings when services are unavailable
