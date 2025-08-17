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

# Add custom CSS for Jeopardy blue theme
st.markdown("""
<style>
    /* Jeopardy blue colors */
    :root {
        --jeopardy-blue: #060CE9;
        --jeopardy-dark-blue: #0520A5;
        --jeopardy-gold: #FFD700;
    }
    
    /* Headers in Jeopardy blue */
    h1, h2, h3 {
        color: #060CE9 !important;
    }
    
    /* Progress bar Jeopardy blue */
    .stProgress > div > div > div > div {
        background-color: #060CE9;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧠 Jay's Jeopardy Trainer")
st.markdown("<p style='color: #060CE9; font-weight: bold; font-size: 1.1em;'>Test your knowledge with real Jeopardy! questions</p>", unsafe_allow_html=True)

# Loading spinner while data is being fetched
with st.spinner("Loading Jeopardy dataset..."):
    df = load_data()

if df.empty:
    st.error("❌ Failed to load Jeopardy dataset.")
    st.info("Check your internet connection or contact the administrator.")
    st.stop()

# Status bar with Jeopardy styling
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.success(f"✅ Loaded {len(df):,} Jeopardy clues!")
with col2:
    if st.session_state.adaptive_mode:
        st.info(f"🎯 Adaptive: ON")
with col3:
    if st.session_state.use_timer:
        st.info(f"⏱️ Timer: {st.session_state.timer_seconds}s")

# Initialize filtered_df as df by default
filtered_df = df

# Check if filtered_df is empty
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
        
        # Find focus areas (accuracy < 50%) and strong areas (accuracy >= 80%)
        # Require at least 3 attempts for reliable statistics
        qualified_cats = category_performance[category_performance['count'] >= 3]
        
        weak_cats = qualified_cats[qualified_cats['mean'] < 0.5]
        st.session_state.weak_categories = dict(zip(weak_cats.index, weak_cats['mean'] * 100))
        
        strong_cats = qualified_cats[qualified_cats['mean'] >= 0.8]
        st.session_state.strong_categories = dict(zip(strong_cats.index, strong_cats['mean'] * 100))
        
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

# Sidebar settings with category filter
with st.sidebar:
    st.markdown("<h2 style='color: #060CE9;'>🎮 Game Settings</h2>", unsafe_allow_html=True)
    
    # Category Filter (moved from main area)
    with st.expander("🏷️ Category Filter", expanded=False):
        categories = sorted(df["category"].unique())
        use_all = st.checkbox("Use all categories", value=True, key="use_all_categories")
        
        if not use_all:
            selected_categories = st.multiselect(
                "Select categories:",
                categories,
                key="category_selector",
                help="Choose specific categories to practice"
            )
            if selected_categories:
                filtered_df = df[df["category"].isin(selected_categories)]
                st.success(f"✅ {len(selected_categories)} categories selected")
            else:
                filtered_df = df
                st.warning("No categories selected - using all")
        else:
            filtered_df = df
            st.info(f"Using all {len(categories)} categories")
    
    # Timer settings in collapsible section
    with st.expander("⏱️ Timer Settings", expanded=True):
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
    
    # Adaptive Training Mode in collapsible section
    with st.expander("🎯 Adaptive Training", expanded=True):
        st.session_state.adaptive_mode = st.checkbox(
            "Enable Adaptive Mode", 
            value=st.session_state.adaptive_mode,
            help="Focuses on categories where you have <50% accuracy after 3+ attempts"
        )
    
        # Show requirements
        with st.expander("How It Works", expanded=False):
            st.write("""
            **Requirements:**
            - Answer at least **3 questions** per category
            - Categories with **<50% accuracy** become focus areas
            - When active, **70% chance** to get questions from focus areas
            
            **Currently tracks:**
            - Category-based performance only
            - Future: Question difficulty, response time patterns
            """)
    
    # Performance Insights section (always visible)
    with st.expander("📊 Performance Insights", expanded=True):
        if st.session_state.history:
            history_df = pd.DataFrame(st.session_state.history)
            category_stats = history_df.groupby('category').agg(
                attempts=('was_correct', 'count'),
                accuracy=('was_correct', 'mean')
            )
            category_stats['accuracy'] *= 100
            
            # Categories with 3+ attempts
            qualified = category_stats[category_stats['attempts'] >= 3]
            
            if not qualified.empty:
                # Focus areas
                focus = qualified[qualified['accuracy'] < 50].sort_values('accuracy')
                if not focus.empty:
                    st.error(f"🎯 Focus Areas ({len(focus)}) - Need practice")
                    for cat in focus.head(5).index:
                        acc = focus.loc[cat, 'accuracy']
                        att = focus.loc[cat, 'attempts']
                        st.caption(f"• {cat}: {acc:.0f}% ({att} attempts)")
                
                # Strong areas
                strong = qualified[qualified['accuracy'] >= 80].sort_values('accuracy', ascending=False)
                if not strong.empty:
                    st.success(f"⭐ Strong Areas ({len(strong)}) - Great job!")
                    for cat in strong.head(5).index:
                        acc = strong.loc[cat, 'accuracy']
                        att = strong.loc[cat, 'attempts']
                        st.caption(f"• {cat}: {acc:.0f}% ({att} attempts)")
                
                # Progress indicator
                total_qualified = len(qualified)
                total_attempted = len(category_stats)
                st.info(f"Progress: {total_qualified}/{total_attempted} categories qualified (3+ attempts)")
                
                if st.session_state.adaptive_mode and st.session_state.weak_categories:
                    st.warning(f"🎯 Adaptive Mode Active - Prioritizing {len(st.session_state.weak_categories)} focus areas")
            else:
                st.info("Answer at least 3 questions per category to see insights")
                if len(category_stats) > 0:
                    st.caption(f"Current: {len(category_stats)} categories attempted")
        else:
            st.info("📊 Start playing to build your performance profile!")

# Display clue with Jeopardy blue styling
st.markdown("<hr style='border: 2px solid #060CE9; margin: 20px 0;'>", unsafe_allow_html=True)

# Display clue with adaptive mode indicator
if st.session_state.adaptive_mode and clue['category'] in st.session_state.weak_categories:
    accuracy = st.session_state.weak_categories[clue['category']]
    # Get attempt count for this category
    if st.session_state.history:
        history_df = pd.DataFrame(st.session_state.history)
        attempts = len(history_df[history_df['category'] == clue['category']])
    else:
        attempts = 0
    st.markdown(f"<h3 style='color: #060CE9; font-family: Arial, sans-serif;'>📚 Category: {clue['category'].upper()}</h3>", unsafe_allow_html=True)
    st.warning(f"🎯 **Focus Area** - Your stats: {accuracy:.0f}% accuracy over {attempts} attempts")
    
    # Clue in Jeopardy-style box
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #060CE9 0%, #0520A5 100%); 
                color: white; 
                padding: 25px; 
                border-radius: 10px; 
                border: 3px solid #FFD700;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <p style='font-size: 1.3em; 
                  margin: 0; 
                  text-align: center;
                  font-family: "Helvetica Neue", Arial, sans-serif;
                  line-height: 1.5;'>{clue['clue']}</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
else:
    st.markdown(f"<h3 style='color: #060CE9; font-family: Arial, sans-serif;'>📚 Category: {clue['category'].upper()}</h3>", unsafe_allow_html=True)

# Clue in Jeopardy-style box
st.markdown(f"""
<div style='background: linear-gradient(135deg, #060CE9 0%, #0520A5 100%); 
            color: white; 
            padding: 25px; 
            border-radius: 10px; 
            border: 3px solid #FFD700;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
    <p style='font-size: 1.3em; 
              margin: 0; 
              text-align: center;
              font-family: "Helvetica Neue", Arial, sans-serif;
              line-height: 1.5;'>{clue['clue']}</p>
</div>
""", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

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
    st.markdown("<hr style='border: 1px solid #060CE9; margin-top: 20px;'>", unsafe_allow_html=True)
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
    st.caption("Showing last 5 responses - see full history below for complete session")
    
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
    
    # Full history in expander with filtering
    with st.expander("📊 View Full Session History"):
        history_df = pd.DataFrame(st.session_state.history)
        history_df["Result"] = history_df["was_correct"].map({True: "✅ Correct", False: "❌ Incorrect"})
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        with col1:
            result_filter = st.selectbox(
                "Filter by result:",
                ["All", "✅ Correct", "❌ Incorrect"],
                key="result_filter"
            )
        with col2:
            categories_in_history = ["All"] + sorted(history_df["category"].unique())
            category_filter = st.selectbox(
                "Filter by category:",
                categories_in_history,
                key="category_filter"
            )
        with col3:
            st.metric("Total Questions", len(history_df))
        
        # Apply filters
        display_df = history_df.copy()
        if result_filter != "All":
            display_df = display_df[display_df["Result"] == result_filter]
        if category_filter != "All":
            display_df = display_df[display_df["category"] == category_filter]
        
        # Show filtered dataframe
        if not display_df.empty:
            st.dataframe(
                display_df[["Result", "category", "clue", "user_response", "correct_response"]],
                use_container_width=True,
                height=400  # Fixed height to avoid excessive scrolling
            )
            st.caption(f"Showing {len(display_df)} of {len(history_df)} total questions")
        else:
            st.info("No questions match the selected filters")
    
    # Progress summary
    st.markdown("---")
    st.subheader("📈 Session Summary")
    col1, col2 = st.columns(2)
    
    with col1:
        # Category performance - only show categories with 3+ attempts
        category_stats = pd.DataFrame(st.session_state.history).groupby("category")["was_correct"].agg(["sum", "count"])
        category_stats["accuracy"] = (category_stats["sum"] / category_stats["count"] * 100).round(1)
        
        # Filter for categories with 3+ attempts and 80%+ accuracy
        best_categories = category_stats[(category_stats["count"] >= 3) & (category_stats["accuracy"] >= 80)]
        best_categories = best_categories.sort_values("accuracy", ascending=False)
        
        if not best_categories.empty:
            st.write("**Best Categories:**")
            for cat, row in best_categories.head(3).iterrows():
                st.write(f"• {cat}: {row['accuracy']}% ({int(row['sum'])}/{int(row['count'])})")
        else:
            st.write("**Best Categories:**")
            st.write("*Need 3+ attempts with 80%+ accuracy*")
    
    with col2:
        st.write("**Session Stats:**")
        st.write(f"• Total Questions: {st.session_state.total}")
        st.write(f"• Correct: {st.session_state.score}")
        st.write(f"• Accuracy: {accuracy:.1f}%")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔁 Practice Missed Questions", use_container_width=True):
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
                    'game_id': retry_question.get('game_id', '')
                }
                # Add embedding if model is available
                if 'clue_embedding' in df.columns and not df.empty:
                    # Try to find matching clue in dataframe for embedding
                    matching = df[df['clue'] == retry_question['clue']]
                    if not matching.empty:
                        st.session_state.current_clue['clue_embedding'] = matching.iloc[0]['clue_embedding']
                    else:
                        st.session_state.current_clue['clue_embedding'] = model.encode(retry_question['clue'])
                
                st.session_state.start_time = datetime.datetime.now()
                st.rerun()
            else:
                st.success("Great job! No missed questions to practice!")
    
    with col2:
        if st.button("🎆 New Random Question", use_container_width=True):
            st.session_state.current_clue = None
            st.rerun()
