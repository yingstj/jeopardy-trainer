"""Firebase configuration for Jaypardy application - SECURE VERSION."""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Firebase configuration - NO HARDCODED SECRETS
FIREBASE_CONFIG: Dict[str, Any] = {
    "apiKey": os.environ.get("FIREBASE_API_KEY"),
    "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.environ.get("FIREBASE_PROJECT_ID"),
    "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.environ.get("FIREBASE_APP_ID"),
    "databaseURL": os.environ.get("FIREBASE_DATABASE_URL")
}

# Firebase Admin SDK configuration - NO HARDCODED SECRETS
FIREBASE_ADMIN_CONFIG = {
    "type": "service_account",
    "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
    "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
    "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
    "auth_uri": os.environ.get("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
    "token_uri": os.environ.get("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
    "auth_provider_x509_cert_url": os.environ.get("FIREBASE_AUTH_PROVIDER_CERT", "https://www.googleapis.com/oauth2/v1/certs"),
    "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_CERT_URL")
}

def get_firebase_config() -> Dict[str, Any]:
    """Get Firebase configuration for client-side use."""
    # Check if required environment variables are set
    required_vars = ["FIREBASE_API_KEY", "FIREBASE_PROJECT_ID"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return FIREBASE_CONFIG

def get_firebase_admin_config() -> Dict[str, Any]:
    """Get Firebase Admin SDK configuration for server-side use."""
    # Check if required environment variables are set
    required_vars = ["FIREBASE_PRIVATE_KEY", "FIREBASE_CLIENT_EMAIL"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return FIREBASE_ADMIN_CONFIG