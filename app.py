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

# Timer settings
if "use_timer" not in st.session_state:
    st.session_state.use_timer = False
    
if "timer_seconds" not in st.session_state:
    st.session_state.timer_seconds = 30

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

# Timer settings in sidebar
with st.sidebar:
    st.header("⏱️ Timer Settings")
    st.session_state.use_timer = st.checkbox("Use Timer", value=st.session_state.use_timer)
    if st.session_state.use_timer:
        st.session_state.timer_seconds = st.slider("Time Limit (seconds):", 5, 60, st.session_state.timer_seconds)
        st.info(f"You have {st.session_state.timer_seconds} seconds to answer")
    else:
        st.info("Timer is OFF - Take your time!")

# Display clue
st.subheader(f"📚 Category: {clue['category']}")
st.markdown(f"**Clue:** {clue['clue']}")

# Timer display
if st.session_state.use_timer:
    elapsed_time = (datetime.datetime.now() - st.session_state.start_time).seconds
    remaining = max(0, st.session_state.timer_seconds - elapsed_time)
    if remaining > 10:
        st.success(f"⏱️ Time remaining: {remaining} seconds")
    elif remaining > 0:
        st.warning(f"⏱️ Time remaining: {remaining} seconds")
    else:
        st.error("⏰ Time's up!")

with st.form(key="clue_form", clear_on_submit=True):
    user_input = st.text_input("Your response:", key="user_response")
    submitted = st.form_submit_button("Submit")

if submitted:
    elapsed_time = (datetime.datetime.now() - st.session_state.start_time).seconds
    user_clean = normalize(user_input)
    answer_clean = normalize(clue["correct_response"])
    
    # Check if correct and within time limit (if timer is on)
    if st.session_state.use_timer:
        correct = user_clean == answer_clean and elapsed_time <= st.session_state.timer_seconds
        timed_out = elapsed_time > st.session_state.timer_seconds
    else:
        correct = user_clean == answer_clean
        timed_out = False

    if correct:
        st.success("✅ Correct!")
        st.session_state.score += 1
    elif timed_out:
        st.error(f"⏰ Time's up! The correct response was: **{clue['correct_response']}**")
    else:
        st.error(f"❌ Incorrect. The correct response was: **{clue['correct_response']}**")

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
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Correct", st.session_state.score)
    with col2:
        st.metric("❌ Incorrect", st.session_state.total - st.session_state.score)
    with col3:
        accuracy = (st.session_state.score / st.session_state.total * 100) if st.session_state.total > 0 else 0
        st.metric("📊 Accuracy", f"{accuracy:.1f}%")

if st.session_state.history:
    st.markdown("---")
    st.subheader("📝 Recent Answers")
    
    # Show last 5 answers in a clean format
    for i, h in enumerate(reversed(st.session_state.history[-5:]), 1):
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                if h["was_correct"]:
                    st.success(f"✅ **{h['category']}**")
                else:
                    st.error(f"❌ **{h['category']}**")
                
                st.write(f"*{h['clue'][:100]}...*" if len(h['clue']) > 100 else f"*{h['clue']}*")
                st.write(f"Your answer: {h['user_response']}")
                if not h["was_correct"]:
                    st.write(f"Correct answer: **{h['correct_response']}**")
            with col2:
                if h["was_correct"]:
                    st.write("✅ Correct")
                else:
                    st.write("❌ Incorrect")
    
    # Full history in expander
    with st.expander("📊 View Full Session History"):
        history_df = pd.DataFrame(st.session_state.history)
        history_df["Result"] = history_df["was_correct"].map({True: "✅", False: "❌"})
        display_df = history_df[["Result", "category", "clue", "user_response", "correct_response"]]
        st.dataframe(display_df, use_container_width=True)
    
    # Progress summary
    st.markdown("---")
    st.subheader("📈 Session Summary")
    col1, col2 = st.columns(2)
    
    with col1:
        # Category performance
        category_stats = pd.DataFrame(st.session_state.history).groupby("category")["was_correct"].agg(["sum", "count"])
        category_stats["accuracy"] = (category_stats["sum"] / category_stats["count"] * 100).round(1)
        category_stats = category_stats.sort_values("accuracy", ascending=False)
        
        st.write("**Best Categories:**")
        for cat, row in category_stats.head(3).iterrows():
            st.write(f"• {cat}: {row['accuracy']}% ({int(row['sum'])}/{int(row['count'])})")
    
    with col2:
        st.write("**Session Stats:**")
        st.write(f"• Total Questions: {st.session_state.total}")
        st.write(f"• Correct: {st.session_state.score}")
        st.write(f"• Accuracy: {accuracy:.1f}%")

    st.markdown("---")
    if st.button("🔁 Practice Missed Questions"):
        missed = [h for h in st.session_state.history if not h["was_correct"]]
        if missed:
            retry = random.choice(missed)
            st.session_state.current_clue = retry
            st.rerun()
        else:
            st.info("Great job! No missed questions to practice!")
