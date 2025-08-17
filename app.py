import streamlit as st
import pandas as pd
import random
import re
import os
import datetime
import time
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
    
    # Try to load local data first
    local_file = "data/all_jeopardy_clues.csv"
    if os.path.exists(local_file):
        try:
            with st.spinner("Loading dataset..."):
                df = pd.read_csv(local_file)
                
            df = df.dropna(subset=["clue", "correct_response"])
            
            # Compute embeddings for all clues (not just 1000)
            with st.spinner(f"Computing embeddings for {len(df)} clues..."):
                # Don't limit to 1000 - use all available clues
                df["clue_embedding"] = df["clue"].apply(lambda x: model.encode(x))
                return df
        except Exception as e:
            st.warning(f"Error loading local data: {e}")
    
    # Fall back to R2 if local file doesn't exist
    try:
        with st.spinner("Loading dataset from Cloudflare R2..."):
            df = load_jeopardy_data_from_r2()
        
        if df.empty:
            st.error("Failed to load dataset from R2. Please check your connection and credentials.")
            return pd.DataFrame()
        
        df = df.dropna(subset=["clue", "correct_response"])
        
        # Compute embeddings for all clues
        with st.spinner(f"Computing embeddings for {len(df)} clues..."):
            # Use all available clues
            df["clue_embedding"] = df["clue"].apply(lambda x: model.encode(x))
            return df
            
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

# Adaptive training mode
if "adaptive_mode" not in st.session_state:
    st.session_state.adaptive_mode = False
    
if "weak_categories" not in st.session_state:
    st.session_state.weak_categories = {}

# Timer settings
if "use_timer" not in st.session_state:
    st.session_state.use_timer = False
    
if "timer_seconds" not in st.session_state:
    st.session_state.timer_seconds = 5

st.title("🧠 Jay's Jeopardy Trainer")

# Loading spinner while data is being fetched
with st.spinner("Loading Jeopardy dataset..."):
    df = load_data()

if df.empty:
    st.error("❌ Failed to load Jeopardy dataset.")
    st.info("Check your internet connection or contact the administrator.")
    st.stop()

st.success(f"✅ Loaded {len(df):,} Jeopardy clues!")

# Show adaptive mode status prominently
if st.session_state.adaptive_mode and st.session_state.weak_categories:
    st.info(f"🎯 **Adaptive Training Active** - Focusing on {len(st.session_state.weak_categories)} categories where you need practice")

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
    # Choose clue based on mode
    if st.session_state.adaptive_mode and st.session_state.history:
        # Adaptive mode: prioritize weak categories
        # Calculate category performance
        history_df = pd.DataFrame(st.session_state.history)
        category_performance = history_df.groupby('category')['was_correct'].agg(['mean', 'count'])
        
        # Find weak categories (accuracy < 50% with at least 3 attempts)
        # This ensures more reliable statistics
        weak_cats = category_performance[(category_performance['mean'] < 0.5) & (category_performance['count'] >= 3)]
        st.session_state.weak_categories = dict(zip(weak_cats.index, weak_cats['mean'] * 100))
        
        if not weak_cats.empty:
            # 70% chance to pick from weak categories
            if random.random() < 0.7:
                weak_category_names = weak_cats.index.tolist()
                weak_clues = filtered_df[filtered_df['category'].isin(weak_category_names)]
                if not weak_clues.empty:
                    st.session_state.current_clue = random.choice(weak_clues.to_dict(orient="records"))
                else:
                    st.session_state.current_clue = random.choice(filtered_df.to_dict(orient="records"))
            else:
                st.session_state.current_clue = random.choice(filtered_df.to_dict(orient="records"))
        else:
            st.session_state.current_clue = random.choice(filtered_df.to_dict(orient="records"))
    else:
        # Normal mode: random selection
        st.session_state.current_clue = random.choice(filtered_df.to_dict(orient="records"))
    
    st.session_state.start_time = datetime.datetime.now()

clue = st.session_state.current_clue

# Sidebar settings
with st.sidebar:
    # Timer settings
    st.header("⏱️ Timer Settings")
    # Check if timer was just enabled
    was_timer_off = not st.session_state.use_timer
    st.session_state.use_timer = st.checkbox("Use Timer", value=st.session_state.use_timer)
    
    # Reset timer if just enabled
    if was_timer_off and st.session_state.use_timer:
        st.session_state.start_time = datetime.datetime.now()
    if st.session_state.use_timer:
        # Use number input with common presets
        col1, col2 = st.columns([2, 1])
        with col1:
            st.session_state.timer_seconds = st.number_input(
                "Time Limit (seconds):",
                min_value=3,
                max_value=60,
                value=st.session_state.timer_seconds,
                step=1,
                help="Enter custom time or use preset"
            )
        with col2:
            st.caption("Quick Set:")
            if st.button("🏆 5s", help="Official Jeopardy"):
                st.session_state.timer_seconds = 5
                st.rerun()
            if st.button("📚 10s", help="Practice mode"):
                st.session_state.timer_seconds = 10
                st.rerun()
            if st.button("🎓 15s", help="Learning mode"):
                st.session_state.timer_seconds = 15
                st.rerun()
        
        if st.session_state.timer_seconds == 5:
            st.success(f"🏆 Official Jeopardy timing: {st.session_state.timer_seconds} seconds")
        else:
            st.info(f"⏱️ You have {st.session_state.timer_seconds} seconds to answer")
    else:
        st.info("Timer is OFF - Take your time!")
    
    # Adaptive Training Mode
    st.header("🎯 Adaptive Training")
    st.session_state.adaptive_mode = st.checkbox(
        "Enable Adaptive Mode", 
        value=st.session_state.adaptive_mode,
        help="Focuses on categories where you have <50% accuracy after 3+ attempts"
    )
    
    # Show requirements
    with st.expander("How Adaptive Mode Works"):
        st.write("""
        **Requirements:**
        - Answer at least **3 questions** per category
        - Categories with **<50% accuracy** become focus areas
        - When active, **70% chance** to get questions from weak categories
        
        **Currently tracks:**
        - Category-based performance only
        - Future: Question difficulty, response time patterns
        """)
    if st.session_state.adaptive_mode:
        if st.session_state.weak_categories:
            st.success(f"📊 Focusing on {len(st.session_state.weak_categories)} weak categories")
            with st.expander("View Focus Areas", expanded=True):
                for cat, acc in sorted(st.session_state.weak_categories.items(), key=lambda x: x[1])[:10]:
                    # Color code by performance
                    if acc < 25:
                        st.error(f"🔴 {cat}: {acc:.0f}%")
                    elif acc < 40:
                        st.warning(f"🟡 {cat}: {acc:.0f}%")
                    else:
                        st.info(f"🟢 {cat}: {acc:.0f}%")
        else:
            st.info("📊 No weak areas identified yet. Answer at least 3 questions per category to build your profile!")
            if st.session_state.history:
                # Show progress toward identification
                history_df = pd.DataFrame(st.session_state.history)
                cat_counts = history_df.groupby('category').size()
                categories_near_threshold = cat_counts[cat_counts >= 2].index.tolist()
                if categories_near_threshold:
                    st.caption(f"Almost there: {len(categories_near_threshold)} categories with 2+ attempts")

# Display clue with adaptive mode indicator
if st.session_state.adaptive_mode and clue['category'] in st.session_state.weak_categories:
    accuracy = st.session_state.weak_categories[clue['category']]
    # Get attempt count for this category
    if st.session_state.history:
        history_df = pd.DataFrame(st.session_state.history)
        attempts = len(history_df[history_df['category'] == clue['category']])
    else:
        attempts = 0
    st.subheader(f"📚 Category: {clue['category']}")
    st.warning(f"🎯 **Focus Area** - Your stats: {accuracy:.0f}% accuracy over {attempts} attempts")
else:
    st.subheader(f"📚 Category: {clue['category']}")
st.markdown(f"**Clue:** {clue['clue']}")

# Timer display - create container first
timer_container = st.container()

# Calculate if time is up BEFORE creating form
time_is_up = False
if st.session_state.use_timer:
    elapsed_time = (datetime.datetime.now() - st.session_state.start_time).total_seconds()
    remaining = max(0, st.session_state.timer_seconds - int(elapsed_time))
    time_is_up = remaining <= 0

# Form with conditional input field
with st.form(key="clue_form", clear_on_submit=True):
    if time_is_up and st.session_state.use_timer:
        # Time's up - disable input field
        st.text_input(
            "Your response:", 
            value="TIME'S UP! Press Buzz to see the answer.",
            disabled=True,
            key="user_response_disabled"
        )
        user_input = ""  # Empty input when time's up
    else:
        # Normal input field
        user_input = st.text_input("Your response:", key="user_response")
    
    submitted = st.form_submit_button("🔔 Buzz!")

# Now display timer above the form using the container
if st.session_state.use_timer:
    with timer_container:
        # Timer already calculated above
        if remaining > 0:
            progress = remaining / st.session_state.timer_seconds
            if remaining > 3:
                st.progress(progress, text=f"⏱️ Time remaining: {remaining} seconds")
            else:
                # Last 3 seconds warning
                st.warning(f"⏱️ Time remaining: {remaining} seconds - HURRY!")
            
            # Auto-refresh for countdown
            time.sleep(1)
            st.rerun()
        else:
            st.error("⏰ Time's up! Press Buzz to reveal the answer.")

if submitted:
    elapsed_time = (datetime.datetime.now() - st.session_state.start_time).seconds
    user_clean = normalize(user_input)
    answer_clean = normalize(clue["correct_response"])
    
    # Check if correct and within time limit (if timer is on)
    if st.session_state.use_timer:
        timed_out = elapsed_time > st.session_state.timer_seconds
        if timed_out:
            correct = False  # Can't be correct if time ran out
        else:
            correct = user_clean == answer_clean
    else:
        correct = user_clean == answer_clean
        timed_out = False

    if correct:
        st.success("✅ Correct!")
        st.session_state.score += 1
    elif timed_out:
        st.error(f"⏰ Time expired! The correct response was: **{clue['correct_response']}**")
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
            # Select a random missed question and use it directly
            retry_question = random.choice(missed)
            # Create a clue dict from the missed question
            st.session_state.current_clue = {
                'category': retry_question['category'],
                'clue': retry_question['clue'],
                'correct_response': retry_question['correct_response'],
                'round': retry_question.get('round', 'Jeopardy'),
                'game_id': retry_question.get('game_id', ''),
                'clue_embedding': model.encode(retry_question['clue'])  # Generate embedding for similarity
            }
            st.session_state.start_time = datetime.datetime.now()
            st.rerun()
        else:
            st.success("Great job! No missed questions to practice!")
