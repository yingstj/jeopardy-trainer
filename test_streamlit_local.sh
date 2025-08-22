#!/bin/bash

# Test Streamlit App Locally
echo "🎯 Testing Jaypardy Streamlit App Locally"
echo "========================================="

# Check if .streamlit directory exists
if [ ! -d ".streamlit" ]; then
    echo "Creating .streamlit directory..."
    mkdir .streamlit
fi

# Check if secrets.toml exists
if [ ! -f ".streamlit/secrets.toml" ]; then
    echo "⚠️  No secrets.toml found!"
    echo "Creating template file..."
    
    cat > .streamlit/secrets.toml << 'EOF'
# Add your Firebase secrets here
# Copy from Streamlit Cloud settings

firebase_project_id = "jaypardy-53a55"
firebase_api_key = "YOUR_API_KEY_HERE"
firebase_auth_domain = "jaypardy-53a55.firebaseapp.com"
firebase_storage_bucket = "jaypardy-53a55.firebasestorage.app"
firebase_messaging_sender_id = "367259134434"
firebase_app_id = "YOUR_APP_ID_HERE"
firebase_database_url = "https://jaypardy-53a55-default-rtdb.firebaseio.com"

# Service Account - Get from Firebase Console
firebase_type = "service_account"
firebase_private_key_id = "YOUR_PRIVATE_KEY_ID"
firebase_client_email = "firebase-adminsdk-xxxxx@jaypardy-53a55.iam.gserviceaccount.com"
firebase_client_id = "YOUR_CLIENT_ID"
firebase_auth_uri = "https://accounts.google.com/o/oauth2/auth"
firebase_token_uri = "https://oauth2.googleapis.com/token"
firebase_auth_provider_cert = "https://www.googleapis.com/oauth2/v1/certs"
firebase_client_cert_url = "YOUR_CERT_URL"

# IMPORTANT: Add your private key here (keep the triple quotes)
firebase_private_key = """-----BEGIN PRIVATE KEY-----
YOUR_PRIVATE_KEY_HERE
-----END PRIVATE KEY-----"""
EOF
    
    echo "✅ Template created at .streamlit/secrets.toml"
    echo "⚠️  Please edit this file and add your actual Firebase secrets!"
    echo ""
    read -p "Press Enter after adding your secrets, or Ctrl+C to exit..."
fi

# Check Python virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -q -r requirements_streamlit.txt

# Create sample questions file if it doesn't exist
if [ ! -f "data/jeopardy_questions.json" ]; then
    echo "Creating sample questions file..."
    mkdir -p data
    cat > data/jeopardy_questions.json << 'EOF'
[
    {
        "category": "SCIENCE",
        "question": "This planet is known as the Red Planet",
        "answer": "Mars",
        "value": 200,
        "round": "Jeopardy!"
    },
    {
        "category": "HISTORY",
        "question": "This president was the first President of the United States",
        "answer": "George Washington",
        "value": 200,
        "round": "Jeopardy!"
    },
    {
        "category": "LITERATURE",
        "question": "This Shakespeare play features star-crossed lovers from feuding families",
        "answer": "Romeo and Juliet",
        "value": 100,
        "round": "Jeopardy!"
    },
    {
        "category": "GEOGRAPHY",
        "question": "This is the longest river in the world",
        "answer": "The Nile",
        "value": 300,
        "round": "Jeopardy!"
    },
    {
        "category": "SPORTS",
        "question": "This sport is known as 'The Beautiful Game'",
        "answer": "Soccer",
        "value": 100,
        "round": "Jeopardy!"
    }
]
EOF
fi

# Run Streamlit app
echo ""
echo "🚀 Starting Streamlit app..."
echo "   URL: http://localhost:8501"
echo "   Press Ctrl+C to stop"
echo ""

streamlit run streamlit_app.py