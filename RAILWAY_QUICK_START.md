# Railway Quick Start Guide

## 🚀 Deploy in 5 Minutes

### 1. Deploy to Railway
```bash
# If using Railway CLI
railway login
railway init
railway up

# Or deploy via GitHub at https://railway.app/new
```

### 2. Add PostgreSQL
In Railway Dashboard:
- Click "New Service" → "Database" → "PostgreSQL"

### 3. Set Environment Variables
In Railway Dashboard → Variables:
```
FLASK_SECRET_KEY=<generate-a-secure-key>
FLASK_ENV=production
```

### 4. Initialize Database
```bash
# Connect to your project
railway link

# Initialize database and load sample data
railway run python manage_db.py init
railway run python manage_db.py load
```

### 5. Verify Deployment
```bash
# Check database status
railway run python manage_db.py check

# View statistics
railway run python manage_db.py stats
```

## 📋 Common Commands

### Load Your Questions
```bash
# If you have a JSON file
railway run python data_processor.py --load-file data/questions.json

# If you have the CSV file
railway run python convert_csv_to_json.py
railway run python data_processor.py --load-file data/questions_sample.json
```

### Database Management
```bash
# Check status
railway run python check_db.py

# View stats
railway run python manage_db.py stats

# Reset database (WARNING: deletes all data)
railway run python manage_db.py reset
```

### Troubleshooting
```bash
# View logs
railway logs

# Check environment variables
railway variables

# Run shell
railway shell
```

## 🔧 Environment Variables

Required:
- `DATABASE_URL` (automatically set by Railway)
- `FLASK_SECRET_KEY` (you must set this)

Optional:
- `FLASK_ENV` (set to 'production')
- `PORT` (automatically set by Railway)

## 📝 Notes

1. Railway automatically provides `DATABASE_URL` when you add PostgreSQL
2. The app automatically detects and uses PostgreSQL when deployed
3. All data is persistent in PostgreSQL
4. Use `railway logs` to debug any issues

## 🆘 Need Help?

1. Check logs: `railway logs`
2. Verify database: `railway run python check_db.py`
3. See full guide: `RAILWAY_DEPLOYMENT.md`