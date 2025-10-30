# Jaypardy! Repository Index

> **Last Updated:** October 30, 2025  
> **Repository:** yingstj/jeopardy-trainer  
> **Primary App:** https://jaypardy.streamlit.app

This document provides a comprehensive index of all files in the repository, their purposes, and relationships.

---

## Table of Contents

1. [Quick Navigation](#quick-navigation)
2. [Core Application Files](#core-application-files)
3. [AI & Game Logic](#ai--game-logic)
4. [Authentication & User Management](#authentication--user-management)
5. [Data Management](#data-management)
6. [Database Files](#database-files)
7. [Scrapers & Data Collection](#scrapers--data-collection)
8. [Deployment & Configuration](#deployment--configuration)
9. [Testing Files](#testing-files)
10. [Documentation](#documentation)
11. [Legacy & Backup Files](#legacy--backup-files)
12. [Directory Structure](#directory-structure)

---

## Quick Navigation

**Start Here:**
- [CLAUDE.md](./CLAUDE.md) - Project documentation & architecture overview
- [README.md](./README.md) - General project information
- [app.py](./app.py) - **Main application entry point**

**Key Components:**
- [ai_opponent.py](./ai_opponent.py) - AI personality system
- [jeopardy_answer_checker.py](./jeopardy_answer_checker.py) - Smart answer validation
- [firebase_auth_streamlit.py](./firebase_auth_streamlit.py) - Authentication helper

---

## Core Application Files

### Main Applications

#### `app.py` ⭐ **PRIMARY APP**
**Purpose:** Complete Jaypardy application with all features  
**Features:**
- Timer with visual countdown
- Two-player mode
- AI opponents with realistic buzzer timing
- Full Jeopardy board (6x5 grid)
- Daily Doubles & Final Jeopardy
- Tournament mode
- 577k+ questions from CSV dataset

**Dependencies:** ai_opponent, firebase_auth_streamlit, jeopardy_answer_checker

#### `app_complete.py`
**Purpose:** Alternative complete implementation  
**Status:** Backup/alternative version of main app

#### `app_basic.py`
**Purpose:** Simplified version without advanced features  
**Use Case:** Testing or minimal deployment

#### `app_ai_only.py`
**Purpose:** Focused on AI opponent features  
**Use Case:** Testing AI functionality in isolation

#### `app_no_auth.py`
**Purpose:** Version without authentication  
**Use Case:** Local testing or public demo

#### `streamlit_app.py`
**Purpose:** Alternative Streamlit entry point  
**Status:** May be legacy or experimental

#### `streamlit_app_with_google.py`
**Purpose:** Streamlit app with Google OAuth integration  
**Features:** Google Sign-In

---

## AI & Game Logic

### AI System

#### `ai_opponent.py` ⭐ **CORE AI LOGIC**
**Purpose:** AI opponent system with 5 personalities  
**Personalities:**
- **Ken Jennings** - History/Literature expert (85% accuracy)
- **Watson** - Science/Tech master (90% accuracy)  
- **Brad Rutter** - Pop Culture specialist (82% accuracy)
- **James Holzhauer** - Sports/Geography expert (88% accuracy)
- **Balanced** - Average player (75% accuracy)

**Functions:**
- `simulate_ai_response()` - Determines if AI answers correctly
- `simulate_buzzer_race()` - Realistic buzzer timing
- `get_ai_daily_double_wager()` - Strategic wagering

#### `ai_engine.py`
**Purpose:** Additional AI logic and utilities  
**Features:** Advanced AI decision-making algorithms

### Answer Validation

#### `jeopardy_answer_checker.py` ⭐ **CRITICAL**
**Purpose:** Smart answer validation preventing false positives  
**Key Features:**
- Word boundary detection (fixes "car" vs "carburetor" bug)
- Last name matching (Washington → George Washington)
- Abbreviation support (JFK → John F. Kennedy)
- Alternative answers (Zimbabwe (or Rhodesia))

**Critical Bug Fix:** Prevents substring false positives

#### `answer_checker.py`
**Purpose:** Basic answer checking utilities  
**Status:** May be superseded by jeopardy_answer_checker.py

---

## Authentication & User Management

### Firebase Authentication

#### `firebase_auth_streamlit.py` ⭐ **AUTH SINGLETON**
**Purpose:** Thread-safe singleton Firebase authentication helper  
**Key Fix:** Prevents multiple Firebase initialization crashes  
**Pattern:** Singleton with threading.Lock

#### `firebase_auth.py`
**Purpose:** Alternative Firebase auth implementation  
**Status:** May be legacy

#### `firebase_config.py`
**Purpose:** Firebase configuration management

#### `firestore_integration.py`
**Purpose:** Firestore database integration for user data

### Other Auth Systems

#### `auth.py`
**Purpose:** Flask-based authentication blueprint  
**Use Case:** API authentication (api/app.py)

#### `auth_manager.py`
**Purpose:** Streamlit-based authentication manager  
**Features:** Session management

#### `user_manager.py`
**Purpose:** User account management utilities

### HTML Templates

#### `google_auth_helper.html`
**Purpose:** OAuth workaround for Streamlit  
**Deployment:** Firebase Hosting (https://jaypardy-53a55.web.app/google_auth_helper.html)  
**Why Needed:** Streamlit Cloud OAuth limitations

---

## Data Management

### Data Loading

#### `r2_jeopardy_data_loader.py`
**Purpose:** Load questions from Cloudflare R2 storage  
**Environment Variables:**
- R2_ENDPOINT_URL
- R2_ACCESS_KEY
- R2_SECRET_KEY
- R2_BUCKET_NAME
- R2_FILE_KEY

#### `load_jeopardy_csv.py`
**Purpose:** Load and process all_jeopardy_clues.csv (577k questions)

#### `load_full_dataset.py`
**Purpose:** Load complete dataset with all fields

#### `load_massive_csv.py`
**Purpose:** Efficiently load large CSV files

#### `load_jarchive_batch.py`
**Purpose:** Batch loading from J-Archive format

#### `download_full_dataset.py`
**Purpose:** Download complete dataset from source

#### `download_github_dataset.py`
**Purpose:** Download dataset from GitHub repository

### Data Processing

#### `data_processor.py`
**Purpose:** Process and transform question data

#### `validate_data.py`
**Purpose:** Validate data integrity and format

#### `convert_csv_to_json.py`
**Purpose:** Convert CSV datasets to JSON format

#### `fix_questions.py`
**Purpose:** Fix malformed questions

#### `fix_jarchive_format.py`
**Purpose:** Fix J-Archive specific formatting issues

#### `generate_100k_questions.py`
**Purpose:** Generate subset of questions for testing

#### `comprehensive_questions.py`
**Purpose:** Create comprehensive question sets

### Analysis Tools

#### `analyze_categories.py`
**Purpose:** Analyze question categories and distribution

#### `analyze_questions.py`
**Purpose:** Analyze question quality and comprehensiveness

#### `category_analyzer.py`
**Purpose:** Streamlit app for category exploration

#### `semantic_explorer.py`
**Purpose:** Semantic similarity search for clues

#### `simple_category_selector.py`
**Purpose:** Simple category filtering UI

#### `theme_manager.py`
**Purpose:** UI theme management

---

## Database Files

### Database Management

#### `database.py`
**Purpose:** Core database operations and schema

#### `init_db.py`
**Purpose:** Initialize database schema

#### `fix_database.py`
**Purpose:** Fix database issues and migrations

#### `manage_db.py`
**Purpose:** Database administration utilities

#### `check_db.py`
**Purpose:** Check database health and stats

#### `db_viewer.py`
**Purpose:** View database contents

#### `migrate_users.py`
**Purpose:** User data migration scripts

### Railway Database (Deployment Platform)

#### `railway_config.py`
**Purpose:** Railway platform configuration

#### `railway_init_db.py`
**Purpose:** Initialize Railway PostgreSQL database

#### `railway_load_csv.py`
**Purpose:** Load CSV data to Railway database

#### `test_railway_db.py`
**Purpose:** Test Railway database connection

#### `get_railway_db_url.py`
**Purpose:** Retrieve Railway database connection string

---

## Scrapers & Data Collection

### Main Scrapers

#### `scraper.py`
**Purpose:** Primary web scraper for Jeopardy questions

#### `scraper_recent.py`
**Purpose:** Scrape recent Jeopardy episodes

#### `j_archive_scraper.py`
**Purpose:** Scrape questions from J-Archive

#### `j_archive_scraper_fixed.py`
**Purpose:** Fixed version of J-Archive scraper

#### `j_archive_simple_scraper.py`
**Purpose:** Simplified J-Archive scraper

### Scripts Directory

#### `scripts/scraper_proper.py`
**Purpose:** Production-ready scraper

#### `scripts/scraper_final.py`
**Purpose:** Final version of scraper

#### `scripts/scraper_fixed.py`
**Purpose:** Bug-fixed scraper

#### `scripts/missed_clue_tracker.py`
**Purpose:** Track and collect missed clues

---

## Deployment & Configuration

### Deployment Scripts

#### `deploy_to_firebase.sh`
**Purpose:** Deploy Google Auth helper to Firebase Hosting  
**Command:** `./deploy_to_firebase.sh`

#### `deploy_with_sqlite.py`
**Purpose:** Deploy version with SQLite database

#### `setup.sh`
**Purpose:** Setup script for fresh installation

#### `setup_local.py`
**Purpose:** Local development setup

#### `start.sh`
**Purpose:** Start the application

#### `run_local.sh`
**Purpose:** Run locally with development settings

#### `test_streamlit_local.sh`
**Purpose:** Test Streamlit app locally

#### `startup.py`
**Purpose:** Application startup logic

### Configuration Files

#### `requirements.txt`
**Purpose:** Python dependencies for production  
**Platform:** General Python environment

#### `requirements_streamlit.txt`
**Purpose:** Streamlit-specific dependencies  
**Platform:** Streamlit Cloud

#### `runtime.txt`
**Purpose:** Python version specification

#### `Procfile`
**Purpose:** Process file for deployment  
**Platforms:** Heroku, Railway

#### `firebase.json`
**Purpose:** Firebase configuration  
**Services:** Hosting, Authentication

#### `railway.json`
**Purpose:** Railway platform configuration

#### `vercel.json`
**Purpose:** Vercel deployment configuration

#### `.streamlit/config.toml`
**Purpose:** Streamlit app configuration

#### `.streamlit/secrets.toml`
**Purpose:** Streamlit secrets (DO NOT COMMIT)

#### `.env.example`
**Purpose:** Environment variable template

#### `.gitignore`
**Purpose:** Git ignore patterns

---

## Testing Files

#### `test_ai_engine.py`
**Purpose:** Test AI opponent logic  
**Command:** `python3 test_ai_engine.py`

#### `test_railway_db.py`
**Purpose:** Test Railway database operations  
**Command:** `python3 test_railway_db.py`

**Note:** jeopardy_answer_checker.py contains self-tests  
**Command:** `python3 jeopardy_answer_checker.py`

---

## Documentation

### Setup & Deployment Guides

#### `CLAUDE.md` ⭐ **PROJECT DOCUMENTATION**
**Purpose:** Comprehensive project documentation for AI assistants  
**Contents:**
- Architecture overview
- Quick commands
- Bug fixes applied
- Development guidelines
- Troubleshooting

#### `README.md`
**Purpose:** Main project README  
**Audience:** General users and developers

#### `README_DATASET.md`
**Purpose:** Dataset documentation  
**Contents:** Data sources, format, statistics

#### `AUTH_SETUP.md`
**Purpose:** Authentication setup instructions

#### `FIREBASE_SETUP.md`
**Purpose:** Firebase configuration guide  
**Services:** Authentication, Hosting

#### `GOOGLE_AUTH_SETUP.md`
**Purpose:** Google OAuth setup instructions

#### `STREAMLIT_DEPLOYMENT.md`
**Purpose:** Streamlit Cloud deployment guide  
**URL:** https://jaypardy.streamlit.app

#### `RAILWAY_DEPLOYMENT.md`
**Purpose:** Railway platform deployment guide

#### `RAILWAY_QUICK_START.md`
**Purpose:** Quick start for Railway deployment

### Security & Maintenance

#### `SECURITY_FIX_INSTRUCTIONS.md`
**Purpose:** Security vulnerability fixes  
**Critical:** Firebase credential regeneration needed

#### `SHARE_GUIDE.md`
**Purpose:** Guide for sharing the app

---

## Legacy & Backup Files

#### `app_backup_20250818_164117.py`
**Purpose:** Backup from August 18, 2025  
**Status:** Archive - do not modify

#### `app_original.py`
**Purpose:** Original app version before major refactoring  
**Status:** Reference only

#### `create_app.py`
**Purpose:** Legacy app creation script  
**Status:** May be obsolete

---

## Directory Structure

### `/data` - Question Datasets

**Main Dataset:**
- `all_jeopardy_clues.csv` ⭐ **577k+ questions** (PRIMARY)
- `questions_sample.json` - 1000 question backup
- `jeopardy_questions_fixed.json` - 220 question fallback

**Other Files:**
- `jeopardy_questions.json` - JSON format questions
- `jeopardy_with_answers.csv` - CSV with answers
- `comprehensive_questions.json` - Curated comprehensive set
- `j_archive_scraped.json` - Scraped from J-Archive
- `category_themes.csv` - Category metadata
- `sample.tsv` - Tab-separated sample
- `sample_questions_fixed.json` - Fixed sample
- `test_questions.json` - Test dataset
- `temp_batch_30.json` - Temporary batch file

### `/scripts` - Utility Scripts

- `scraper_proper.py` - Production scraper
- `scraper_final.py` - Final scraper version
- `scraper_fixed.py` - Bug-fixed scraper
- `missed_clue_tracker.py` - Track missed clues

### `/api` - API Server

- `app.py` - Flask API server for alternative interface

### `/templates` - HTML Templates

**Firebase Templates:**
- `firebase_login.html` - Firebase login page
- `firebase_register.html` - Firebase registration
- `firebase_profile.html` - User profile

**General Templates:**
- `base.html` - Base template
- `login.html` - Login page
- `register.html` - Registration page
- `profile.html` - Profile page
- `landing.html` - Landing page
- `jeopardy_trainer.html` - Main game interface
- `jeopardy_simple.html` - Simplified interface

### `/.streamlit` - Streamlit Configuration

- `config.toml` - App configuration
- `secrets.toml` - Secrets (gitignored)

### `/.devcontainer` - Development Container

- `devcontainer.json` - VS Code dev container config

---

## File Relationships

### Dependency Graph

```
app.py (MAIN)
├── ai_opponent.py
├── firebase_auth_streamlit.py
│   └── firebase_config.py
└── jeopardy_answer_checker.py

Data Loading:
├── r2_jeopardy_data_loader.py
├── load_jeopardy_csv.py
└── data/all_jeopardy_clues.csv
```

### Data Flow

1. **Question Loading:** `r2_jeopardy_data_loader.py` → Cloudflare R2 → `data/all_jeopardy_clues.csv`
2. **Authentication:** User → `firebase_auth_streamlit.py` → Firebase
3. **Game Logic:** `app.py` → `ai_opponent.py` → AI response
4. **Answer Validation:** User answer → `jeopardy_answer_checker.py` → Match result

---

## Development Workflow

### Local Development
```bash
# Setup
pip install -r requirements.txt

# Run locally
streamlit run app.py

# Run tests
python3 jeopardy_answer_checker.py
python3 test_ai_engine.py
```

### Deployment
```bash
# Deploy to Firebase (Google Auth)
./deploy_to_firebase.sh

# Deploy to Streamlit Cloud
# Push to main branch (auto-deploys)
```

---

## Key Files Summary

| File | Priority | Purpose |
|------|----------|---------|
| `app.py` | ⭐⭐⭐ | Main application |
| `ai_opponent.py` | ⭐⭐⭐ | AI personality system |
| `jeopardy_answer_checker.py` | ⭐⭐⭐ | Answer validation (critical) |
| `firebase_auth_streamlit.py` | ⭐⭐⭐ | Authentication singleton |
| `CLAUDE.md` | ⭐⭐⭐ | Project documentation |
| `data/all_jeopardy_clues.csv` | ⭐⭐⭐ | 577k questions dataset |
| `r2_jeopardy_data_loader.py` | ⭐⭐ | R2 data loading |
| `requirements.txt` | ⭐⭐ | Dependencies |
| `README.md` | ⭐⭐ | General documentation |

---

## External Resources

- **Live App:** https://jaypardy.streamlit.app
- **Google Auth Helper:** https://jaypardy-53a55.web.app/google_auth_helper.html
- **Firebase Console:** https://console.firebase.google.com/project/jaypardy-53a55
- **J-Archive Source:** https://j-archive.com
- **Streamlit Dashboard:** https://share.streamlit.io/

---

## Common Tasks

### Adding New Features
1. Modify `app.py` or create new component file
2. Update `CLAUDE.md` documentation
3. Test locally with `streamlit run app.py`
4. Push to main for auto-deployment

### Fixing Bugs
1. Identify affected component
2. Check `CLAUDE.md` for known issues
3. Test with `python3 <file>.py` if applicable
4. Update documentation

### Updating Questions
1. Modify `data/all_jeopardy_clues.csv`
2. Validate with `validate_data.py`
3. Test loading with `load_jeopardy_csv.py`

### Security Updates
1. Review `SECURITY_FIX_INSTRUCTIONS.md`
2. Regenerate Firebase credentials (CRITICAL)
3. Update `.streamlit/secrets.toml`

---

## Notes

- **Firebase Private Key:** Exposed in commits, needs regeneration (see SECURITY_FIX_INSTRUCTIONS.md)
- **Primary Dataset:** 577k questions in `data/all_jeopardy_clues.csv`
- **Deployment:** Auto-deploys on push to main branch
- **Testing:** Run answer checker tests before committing changes

---

*This index is maintained to help developers quickly understand and navigate the repository structure.*
