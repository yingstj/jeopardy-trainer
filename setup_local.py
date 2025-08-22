#!/usr/bin/env python3
"""
Local setup script for Jay's Jeopardy Trainer
This script helps users set up the app on their local machine
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a shell command and handle errors"""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🧠 Jay's Jeopardy Trainer - Local Setup")
    print("=" * 40)
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("❌ Python 3.8+ is required")
        print(f"   You have: Python {python_version.major}.{python_version.minor}")
        sys.exit(1)
    
    print(f"✅ Python {python_version.major}.{python_version.minor} detected")
    
    # Create virtual environment if it doesn't exist
    venv_path = Path("venv")
    if not venv_path.exists():
        if not run_command("python3 -m venv venv", "Creating virtual environment"):
            sys.exit(1)
    else:
        print("✅ Virtual environment already exists")
    
    # Determine pip command based on OS
    if os.name == 'nt':  # Windows
        pip_cmd = "venv\\Scripts\\pip"
        python_cmd = "venv\\Scripts\\python"
        activate_cmd = "venv\\Scripts\\activate"
    else:  # Unix/Linux/Mac
        pip_cmd = "venv/bin/pip"
        python_cmd = "venv/bin/python"
        activate_cmd = "source venv/bin/activate"
    
    # Upgrade pip
    run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip")
    
    # Install requirements
    if not run_command(f"{pip_cmd} install -r requirements.txt", "Installing dependencies"):
        print("\n⚠️  Some dependencies failed to install")
        print("   You can try installing them manually")
    
    # Create necessary directories
    Path("user_data").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    print("✅ Created data directories")
    
    # Check for data file
    data_file = Path("data/all_jeopardy_clues.csv")
    if data_file.exists():
        # Get file size in MB
        size_mb = data_file.stat().st_size / (1024 * 1024)
        print(f"✅ Jeopardy data found ({size_mb:.1f} MB)")
    else:
        print("⚠️  No Jeopardy data found")
        print("   The app will download data on first run")
    
    # Create .streamlit directory if it doesn't exist
    streamlit_dir = Path(".streamlit")
    streamlit_dir.mkdir(exist_ok=True)
    
    # Check for secrets file
    secrets_file = streamlit_dir / "secrets.toml"
    if not secrets_file.exists():
        print("\n📝 Creating secrets template...")
        secrets_template = streamlit_dir / "secrets.toml.example"
        if secrets_template.exists():
            print("   Copy .streamlit/secrets.toml.example to .streamlit/secrets.toml")
            print("   and add your Google OAuth credentials (optional)")
    
    print("\n" + "=" * 40)
    print("✅ Setup complete!")
    print("\nTo run the app:")
    print(f"  1. Activate virtual environment: {activate_cmd}")
    print("  2. Run the app: streamlit run app.py")
    print("\nThe app will open at: http://localhost:8501")
    
    # Ask if user wants to run now
    print("\n" + "=" * 40)
    response = input("Would you like to run the app now? (y/n): ").lower()
    if response == 'y':
        print("\n🚀 Starting Jay's Jeopardy Trainer...")
        if os.name == 'nt':  # Windows
            subprocess.run(f"{python_cmd} -m streamlit run app.py", shell=True)
        else:
            subprocess.run(f"{python_cmd} -m streamlit run app.py", shell=True)

if __name__ == "__main__":
    main()