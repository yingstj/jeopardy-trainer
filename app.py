import streamlit as st
import pandas as pd
import random
import re
import os
import datetime
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Import the R2 data loader
from r2_jeopardy_data_loader import load_jeopardy_data_from_r2

# Load model once
@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

model = load_model()

# Normalize text for fuzzy matching
def normalize(text):
    text = text.lower()
    text = re.sub(r"^(what|who|where|when|why|how)\s+(is|are|was|were)\s+", "", text)
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text.strip()

# Load and filter data
@st.cache_data
def load_data():
    # Check if we're in a GitHub Actions environment (for CI testing)
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        # Return a small sample dataset for testing
        return pd.DataFrame({
            'category': ['HISTORY', 'SCIENCE', 'MOVIES'],
            'clue': ['First president of the US', 'Element with symbol H', 'This film won Best Picture in 2020'],
            'correct_response': ['George Washington', 'Hydrogen', 'Parasite'],
            'round': ['Jeopardy', 'Jeopardy', 'Double Jeopardy'],
            'game_id': ['1', '1', '2']
        })
    
    try:
        # Load from R2
        with st.spinner("Loading dataset from Cloudflare R2..."):
            df = load_jeopardy_data_from_r2()
        
        if df.empty:
            st.error("Failed to load dataset from R2. Please check your connection and credentials.")
            return pd.DataFrame()
        
        df = df.dropna(subset=["clue", "correct_response"])
        
        # Compute embeddings (can be expensive, so we'll do it on demand)
        with st.spinner("Computing clue embeddings..."):
            # Process in batches to avoid memory issues
            batch_size = min(1000, len(df))
            sample_df = df.sample(n=batch_size) if len(df) > batch_size else df
            sample_df["clue_embedding"] = sample_df["clue"].apply(lambda x: model.encode(x))
            return sample_df
            
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Initialize global variables and session state
model = load_model()

# Track session state
if "history" not in st.session_state:
    st.session_state.history = []

if "score" not in st.session_state:
    st.session_state.score = 0
    st.session_state.total = 0

if "start_time" not in st.session_state:
    st.session_state.start_time = datetime.datetime.now()

if "current_clue" not in st.session_state:
    st.session_state.current_clue = None

# Progress tracking uses memory instead of file storage for Streamlit Cloud compatibility
if "progress_data" not in st.session_state:
    st.session_state.progress_data = []

st.title("🧠 Jay's Jeopardy Trainer")

# Loading spinner while data is being fetched
with st.spinner("Loading Jeopardy dataset..."):
    df = load_data()

if df.empty:
    st.error("❌ Failed to load Jeopardy dataset.")
    st.info("Check your internet connection or contact the administrator.")
    st.stop()

st.success(f"✅ Loaded {len(df)} Jeopardy clues!")

# Optional category filtering
with st.expander("🏷️ Filter by Category (Optional)"):
    categories = sorted(df["category"].unique())
    all_categories = st.checkbox("Use all categories", value=True)
    
    if not all_categories:
        selected_categories = st.multiselect("Select categories:", categories)
        if selected_categories:
            filtered_df = df[df["category"].isin(selected_categories)]
        else:
            filtered_df = df
    else:
        filtered_df = df

if filtered_df.empty:
    st.warning("No clues found for the selected categories. Please select different categories.")
    st.stop()

if st.session_state.current_clue is None:
    st.session_state.current_clue = random.choice(filtered_df.to_dict(orient="records"))
    st.session_state.start_time = datetime.datetime.now()

clue = st.session_state.current_clue
st.subheader(f"📚 Category: {clue['category']}")
st.markdown(f"**Clue:** {clue['clue']}")

time_limit = st.slider("⏱️ Time Limit (seconds):", 10, 60, 30)

with st.form(key="clue_form"):
    user_input = st.text_input("Your response:")
    submitted = st.form_submit_button("Submit")

if submitted:
    elapsed_time = (datetime.datetime.now() - st.session_state.start_time).seconds
    user_clean = normalize(user_input)
    answer_clean = normalize(clue["correct_response"])
    correct = user_clean == answer_clean and elapsed_time <= time_limit

    if correct:
        st.success("✅ Correct!")
        st.session_state.score += 1
    else:
        st.error(f"❌ Incorrect or timed out. The correct response was: *{clue['correct_response']}*")

        # Semantic similarity
        if "clue_embedding" in filtered_df.columns:
            user_vector = model.encode(clue["clue"])
            clue_vectors = np.vstack(filtered_df["clue_embedding"].values)
            similarities = cosine_similarity([user_vector], clue_vectors)[0]
            top_indices = similarities.argsort()[-4:][::-1]
            similar_clues = filtered_df.iloc[top_indices]

            with st.expander("🔍 Review similar clues"):
                for _, row in similar_clues.iterrows():
                    st.markdown(f"- **{row['category']}**: {row['clue']}")
                    st.markdown(f"  → *{row['correct_response']}*")

    st.session_state.total += 1
    st.session_state.history.append({
        "game_id": clue.get("game_id", ""),
        "category": clue["category"],
        "clue": clue["clue"],
        "correct_response": clue["correct_response"],
        "round": clue.get("round", ""),
        "user_response": user_input,
        "was_correct": correct
    })

    # Update in-memory progress tracking
    today = datetime.date.today().isoformat()
    st.session_state.progress_data.append({
        "date": today,
        "total": 1,
        "correct": 1 if correct else 0
    })

    st.session_state.current_clue = None
    st.rerun()

if st.session_state.total:
    st.markdown("---")
    st.metric("Your Score", f"{st.session_state.score} / {st.session_state.total}")

if st.session_state.history:
    st.subheader("📊 Session Recap")
    st.dataframe(pd.DataFrame(st.session_state.history))

    with st.expander("📈 Progress Tracker"):
        if st.session_state.progress_data:
            progress_df = pd.DataFrame(st.session_state.progress_data)
            summary = progress_df.groupby("date").sum().reset_index()
            summary["accuracy"] = (summary["correct"] / summary["total"]).round(2)
            st.dataframe(summary)
        else:
            st.info("No progress data available yet.")

    st.markdown("---")
    if st.button("🔁 Adaptive Retry Mode"):
        missed = [h for h in st.session_state.history if not h["was_correct"]]
        if missed:
            retry = random.choice(missed)
            st.session_state.current_clue = retry
            st.rerun()
        else:
            st.info("No missed clues yet to retry!")
