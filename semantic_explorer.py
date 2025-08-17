import streamlit as st
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os

# Import the R2 data loader
from r2_jeopardy_data_loader import load_jeopardy_data_from_r2

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
        
        return df.dropna(subset=["clue"])
            
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

@st.cache_data
def compute_embeddings(df, model, max_samples=1000):
    # Use a sample for large datasets to avoid memory issues
    if len(df) > max_samples:
        sample_df = df.sample(n=max_samples)
        return model.encode(sample_df["clue"].tolist(), show_progress_bar=True), sample_df
    else:
        return model.encode(df["clue"].tolist(), show_progress_bar=True), df

st.title("🔍 Semantic Clue Explorer")

with st.spinner("Loading Jeopardy dataset..."):
    df = load_data()

if df.empty:
    st.error("❌ Failed to load Jeopardy dataset.")
    st.info("Check your internet connection or contact the administrator.")
    st.stop()

st.success(f"✅ Loaded {len(df)} Jeopardy clues!")

# Memory efficiency warning for large datasets
if len(df) > 10000:
    st.warning(f"⚠️ Large dataset detected ({len(df)} clues). Using a sample of 1000 clues for search to ensure performance.")

query = st.text_input("Enter a topic, keyword, or concept:")
model = load_model()

if not df.empty and query:
    with st.spinner("Searching for related clues..."):
        # Get embeddings (sampling if necessary)
        embeddings, working_df = compute_embeddings(df, model)
        
        # Encode query and compute similarity
        query_embedding = model.encode([query])
        sims = cosine_similarity(query_embedding, embeddings)[0]
        
        # Add similarity scores to the working dataframe
        working_df = working_df.copy()
        working_df["similarity"] = sims
        
        # Sort and display results
        top_matches = working_df.sort_values("similarity", ascending=False).head(10)
        
        st.subheader("Top Matching Clues")
        for _, row in top_matches.iterrows():
            st.markdown(f"**Category:** {row['category']}  \n"
                        f"**Clue:** {row['clue']}  \n"
                        f"**Answer:** *{row['correct_response']}*  \n"
                        f"**Round:** {row.get('round', 'Unknown')}  \n"
                        f"**Similarity:** {row['similarity']:.2f}")
            st.markdown("---")
