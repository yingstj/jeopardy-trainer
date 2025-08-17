# How to Share Jay's Jeopardy Trainer

## Quick Start for Recipients

### Option 1: One-Click Setup (Mac/Linux)
```bash
./run_local.sh
```

### Option 2: Manual Setup
```bash
python3 setup_local.py
```

### Option 3: Step-by-Step
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Mac/Linux
# OR
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## Sharing Methods

### 1. Share via GitHub (Recommended)

**For the Sender:**
1. Create a GitHub repository
2. Upload all files except:
   - `venv/` folder
   - `user_data/` folder
   - `.streamlit/secrets.toml` (if exists)
   - Large CSV files in `data/` (optional)

3. Share the repository link

**For Recipients:**
```bash
# Clone the repository
git clone <repository-url>
cd jay-jeopardy-trainer

# Run setup
./run_local.sh
```

### 2. Share via ZIP File

**For the Sender:**
```bash
# Create a clean copy for sharing
zip -r jeopardy-trainer.zip . \
  -x "venv/*" \
  -x "user_data/*" \
  -x ".streamlit/secrets.toml" \
  -x "*.pyc" \
  -x "__pycache__/*" \
  -x ".DS_Store"
```

**For Recipients:**
1. Unzip the file
2. Open terminal in the folder
3. Run: `./run_local.sh`

### 3. Deploy Online (Public Access)

**Streamlit Cloud (Free):**
1. Push to GitHub (see method 1)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Deploy the app
5. Share the URL

**Features work differently online:**
- Data is shared between all users
- No local file storage
- Authentication recommended

## System Requirements

- Python 3.8 or higher
- 500 MB free disk space
- Internet connection (first run only)

## First Run Instructions

When recipients run the app for the first time:

1. **Authentication**: 
   - Enter any email to create an account
   - No real email verification required for local use
   - Progress saves automatically

2. **Data Loading**:
   - The app will load sample data initially
   - Full dataset downloads on first use
   - Takes 1-2 minutes depending on connection

3. **Customization**:
   - Timer is off by default (toggle in sidebar)
   - All categories selected by default
   - Adaptive mode available after 3+ questions per category

## Troubleshooting for Recipients

### "Python not found"
- Install Python from [python.org](https://python.org)
- Make sure to check "Add to PATH" during installation

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### App won't start
```bash
# Try manual start
python3 -m streamlit run app.py
```

### Port already in use
```bash
# Use a different port
streamlit run app.py --server.port 8502
```

## Included Files

Essential files to share:
- `app.py` - Main application
- `requirements.txt` - Dependencies
- `run_local.sh` - Quick start script
- `setup_local.py` - Setup wizard
- `auth_manager.py` - Authentication system
- `scraper_v2.py` - Data collector (optional)

Optional files:
- `AUTH_SETUP.md` - Authentication guide
- `SHARE_GUIDE.md` - This file
- `test_auth.py` - Authentication tester
- `data/` folder - Pre-downloaded data (speeds up first run)

## Privacy & Data

- All data stays on the recipient's computer
- No external servers except for initial data download
- User progress saved locally in `user_data/` folder
- Authentication is local only (no real email verification)

## Support

Recipients can:
1. Check this guide for help
2. Run `python3 test_auth.py` to test authentication
3. Delete `user_data/` folder to reset all progress
4. Re-run `./run_local.sh` to fix most issues