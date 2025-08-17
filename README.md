# Jay's Jeopardy Trainer

A Streamlit app that helps you practice Jeopardy questions with a large dataset stored in Cloudflare R2.

## Features

- Train with a large collection of real Jeopardy clues and responses
- Filter by category
- Adjustable time limits
- Track your progress within each session
- Semantic similarity search to find related clues
- Adaptive retry mode to focus on clues you've missed

## How It Works

1. The app loads Jeopardy clues from a Cloudflare R2 bucket
2. You can filter by categories you're interested in
3. The app presents clues and you try to answer them within the time limit
4. Your progress is tracked throughout your session
5. For incorrect answers, the app shows you similar clues to help you learn

## 🚀 Deployment Options

Jay's Jeopardy Trainer can be deployed on multiple platforms. Here are the most popular options:

### Quick Deployment Options

| Platform | Difficulty | Cost | Best For |
|----------|------------|------|----------|
| **[Streamlit Cloud](https://share.streamlit.io)** | ⭐ Easy | 🆓 Free | Public apps, sharing |
| **[Railway](https://railway.app)** | ⭐ Easy | 🆓 Free tier | Quick cloud deployment |
| **[Render](https://render.com)** | ⭐ Easy | 🆓 Free tier | Alternative cloud option |
| **[Heroku](https://heroku.com)** | ⭐⭐ Medium | 💰 $5/month | Traditional PaaS |
| **[Docker](./DEPLOYMENT.md#docker-deployment)** | ⭐⭐ Medium | Varies | Containerized deployment |

### 🌟 Recommended: Streamlit Cloud (Free & Easy)

1. Fork this repository to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account and select this repository
4. Deploy with one click!

### 📚 Complete Deployment Guide

For detailed instructions on all deployment options, including:
- Local development setup
- Cloud platform configurations
- Docker containerization
- Self-hosted VPS deployment
- Environment variable setup
- Troubleshooting tips

**👉 See [DEPLOYMENT.md](./DEPLOYMENT.md) for the complete guide**

### Environment Variables (Optional)

For cloud deployments, you can configure these environment variables to use your own Cloudflare R2 storage:

- `R2_ENDPOINT_URL`: Your Cloudflare R2 endpoint URL
- `R2_ACCESS_KEY`: Your R2 access key
- `R2_SECRET_KEY`: Your R2 secret key
- `R2_BUCKET_NAME`: Your R2 bucket name (default: jeopardy-dataset)
- `R2_FILE_KEY`: The name of your dataset file (default: all_jeopardy_clues.csv)

*Note: The app works without these variables using default sample data.*

## Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/jay-jeopardy-trainer.git
   cd jay-jeopardy-trainer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:
   ```bash
   streamlit run app.py
   ```

## Files

- `app.py` - Main Streamlit application
- `r2_jeopardy_data_loader.py` - Module to load data from Cloudflare R2
- `semantic_explorer.py` - Tool for exploring semantically similar clues
- `requirements.txt` - Dependencies for deployment
