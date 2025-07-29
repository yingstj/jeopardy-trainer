# Railway Deployment Guide for Jeopardy AI Trainer

This guide will help you deploy and load your database on Railway.

## Prerequisites

1. Railway account (sign up at https://railway.app)
2. Railway CLI installed (optional but recommended)
3. Git repository with your code

## Step 1: Deploy to Railway

### Option A: Deploy via GitHub (Recommended)

1. Push your code to GitHub
2. Go to https://railway.app/new
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will automatically detect your app

### Option B: Deploy via Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize new project
railway init

# Deploy
railway up
```

## Step 2: Add PostgreSQL Database

1. In your Railway project dashboard:
   - Click "New Service"
   - Select "Database"
   - Choose "PostgreSQL"
   - Railway will automatically provision a PostgreSQL database

2. Railway will automatically inject the `DATABASE_URL` environment variable

## Step 3: Set Environment Variables

In your Railway project settings, add these environment variables:

```bash
FLASK_SECRET_KEY=your-very-secret-key-here-change-this
FLASK_ENV=production
```

## Step 4: Initialize the Database

### Method 1: Using Railway CLI (Recommended)

```bash
# Connect to your Railway project
railway link

# Initialize the database tables
railway run python init_db.py

# Load sample questions (if you have them)
railway run python init_db.py --load-sample
```

### Method 2: Using Railway Shell

1. In your Railway dashboard, click on your app service
2. Go to "Settings" → "Deploy" → "Shell"
3. Run these commands:

```bash
# Initialize database
python init_db.py

# Load questions from your JSON file
python data_processor.py --load-file data/questions_sample.json
```

### Method 3: One-Time Job

Create a temporary initialization service:

1. Create a new file `railway.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python init_db.py && python data_processor.py --load-file data/questions_sample.json",
    "restartPolicyType": "NEVER"
  }
}
```

2. Deploy this as a separate service, then remove it after initialization

## Step 5: Load Your Jeopardy Questions

### If you have questions in JSON format:

```bash
# Using Railway CLI
railway run python data_processor.py --load-file data/questions_sample.json

# Or load from the CSV converter
railway run python convert_csv_to_json.py
railway run python data_processor.py --load-file data/questions_sample.json
```

### If you need to fetch new questions:

```bash
# This will use the scraper (if implemented)
railway run python data_processor.py --fetch
```

## Step 6: Verify Deployment

1. Check your app URL (provided by Railway)
2. Try to register a new user
3. Check if questions are loaded by playing a game

## Troubleshooting

### Database Connection Issues

1. Verify DATABASE_URL is set:
```bash
railway variables
```

2. Check logs:
```bash
railway logs
```

### Questions Not Loading

1. Check if database tables exist:
```bash
railway run python -c "from database import JeopardyDatabase; db = JeopardyDatabase(); print('DB initialized')"
```

2. Check question count:
```bash
railway run python -c "from database import JeopardyDatabase; db = JeopardyDatabase(); cats = db.get_categories(); print(f'Total categories: {len(cats)}')"
```

### Memory Issues

If you get memory errors while loading questions:

1. Load questions in smaller batches
2. Modify `convert_csv_to_json.py` to process fewer questions at a time

## Maintenance Commands

```bash
# View database statistics
railway run python data_processor.py --stats

# Update difficulty ratings
railway run python data_processor.py --update-difficulty

# Clean up old sessions
railway run python -c "from database import JeopardyDatabase; db = JeopardyDatabase(); db.cleanup_old_sessions(30)"
```

## Production Checklist

- [ ] Change FLASK_SECRET_KEY to a secure value
- [ ] Set FLASK_ENV to 'production'
- [ ] Initialize database tables
- [ ] Load question data
- [ ] Test user registration and login
- [ ] Verify questions are displayed
- [ ] Check that progress tracking works

## Monitoring

Railway provides built-in monitoring:
- Check logs: `railway logs`
- View metrics in Railway dashboard
- Set up health checks in Railway settings

## Backup and Restore

### Backup your database:
```bash
# Create backup using Railway CLI
railway run pg_dump $DATABASE_URL > backup.sql
```

### Restore from backup:
```bash
# Restore backup
railway run psql $DATABASE_URL < backup.sql
```