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

## Deployment

This app is designed to be deployed on Streamlit Cloud, which provides free hosting for Streamlit apps.

### Environment Variables

The app requires these environment variables (set as Streamlit secrets):

- `R2_ENDPOINT_URL`: Your Cloudflare R2 endpoint URL
- `R2_ACCESS_KEY`: Your R2 access key
- `R2_SECRET_KEY`: Your R2 secret key
- `R2_BUCKET_NAME`: Your R2 bucket name (default: jeopardy-dataset)
- `R2_FILE_KEY`: The name of your dataset file (default: all_jeopardy_clues.csv)

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
