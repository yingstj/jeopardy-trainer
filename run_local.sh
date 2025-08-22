#!/bin/bash

echo "🧠 Jay's Jeopardy Trainer - Quick Start"
echo "========================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if requirements are installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Create necessary directories
mkdir -p user_data data .streamlit

# Start the app
echo ""
echo "🚀 Starting Jay's Jeopardy Trainer..."
echo "   The app will open at: http://localhost:8501"
echo "   Press Ctrl+C to stop"
echo ""

streamlit run app.py