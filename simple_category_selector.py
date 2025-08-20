"""
Simplified category selector that works better with real Jeopardy data
"""
import streamlit as st
import pandas as pd
import random
from typing import List

def create_simple_category_selector(df: pd.DataFrame) -> List[str]:
    """
    Create a simplified but effective category selector
    """
    all_categories = sorted(df["category"].unique())
    
    # Calculate category frequencies
    category_counts = df['category'].value_counts()
    
    # Get most common categories
    top_100 = category_counts.head(100).index.tolist()
    top_500 = category_counts.head(500).index.tolist()
    top_1000 = category_counts.head(1000).index.tolist()
    
    st.markdown("### 📚 Category Selection")
    
    selection_mode = st.radio(
        "Selection Method:",
        ["🎯 Popular Categories", "🔍 Search & Select", "🎲 Random Selection", "📝 Manual Selection"],
        horizontal=False
    )
    
    selected_categories = []
    
    if selection_mode == "🎯 Popular Categories":
        preset = st.selectbox(
            "Choose a preset:",
            [
                "Top 50 Most Common",
                "Top 100 Most Common", 
                "Top 250 Most Common",
                "Top 500 Most Common",
                "Top 1000 Most Common"
            ]
        )
        
        if "50" in preset:
            selected_categories = category_counts.head(50).index.tolist()
        elif "100" in preset:
            selected_categories = category_counts.head(100).index.tolist()
        elif "250" in preset:
            selected_categories = category_counts.head(250).index.tolist()
        elif "500" in preset:
            selected_categories = category_counts.head(500).index.tolist()
        elif "1000" in preset:
            selected_categories = category_counts.head(1000).index.tolist()
        
        # Show some examples
        st.info(f"Selected {len(selected_categories)} most frequently used categories")
        with st.expander("View selected categories"):
            # Show in columns
            cols = st.columns(3)
            for i, cat in enumerate(selected_categories[:30]):
                count = category_counts[cat]
                cols[i % 3].write(f"• {cat} ({count} Qs)")
            if len(selected_categories) > 30:
                st.write(f"... and {len(selected_categories) - 30} more")
    
    elif selection_mode == "🔍 Search & Select":
        # Search functionality
        search_term = st.text_input(
            "Search categories (e.g., 'history', 'science', 'movie'):",
            help="Enter keywords to filter categories"
        )
        
        if search_term:
            # Filter categories by search term
            filtered = [cat for cat in all_categories if search_term.lower() in cat.lower()]
            
            if filtered:
                st.success(f"Found {len(filtered)} matching categories")
                
                # Option to select all or choose specific ones
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Select All Matches", use_container_width=True):
                        selected_categories = filtered
                with col2:
                    if st.button("Clear", use_container_width=True):
                        selected_categories = []
                
                # Manual selection from filtered
                selected_categories = st.multiselect(
                    f"Select from {len(filtered)} matches:",
                    filtered,
                    default=filtered[:min(20, len(filtered))]
                )
            else:
                st.warning("No categories match your search")
        else:
            st.info("Enter a search term to find categories")
    
    elif selection_mode == "🎲 Random Selection":
        num_random = st.slider(
            "Number of random categories:",
            min_value=10,
            max_value=500,
            value=100,
            step=10
        )
        
        if st.button("🎲 Generate Random Selection", type="primary"):
            selected_categories = random.sample(all_categories, min(num_random, len(all_categories)))
            st.success(f"Randomly selected {len(selected_categories)} categories")
        
        # Show current selection if any
        if 'random_categories' in st.session_state:
            selected_categories = st.session_state.random_categories
            with st.expander(f"Current selection ({len(selected_categories)} categories)"):
                for cat in selected_categories[:20]:
                    st.write(f"• {cat}")
                if len(selected_categories) > 20:
                    st.write(f"... and {len(selected_categories) - 20} more")
        
        # Store in session state
        if selected_categories:
            st.session_state.random_categories = selected_categories
    
    else:  # Manual Selection
        # Provide some quick filters
        st.write("Quick filters to help narrow down:")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.checkbox("Contains 'HISTORY'"):
                filtered = [c for c in all_categories if 'HISTORY' in c.upper()]
                selected_categories.extend(filtered)
        
        with col2:
            if st.checkbox("Contains 'SCIENCE'"):
                filtered = [c for c in all_categories if 'SCIENCE' in c.upper()]
                selected_categories.extend(filtered)
        
        with col3:
            if st.checkbox("Contains 'MOVIES' or 'TV'"):
                filtered = [c for c in all_categories if any(word in c.upper() for word in ['MOVIE', 'TV', 'FILM'])]
                selected_categories.extend(filtered)
        
        # Remove duplicates
        selected_categories = list(set(selected_categories))
        
        # Manual multiselect
        selected_categories = st.multiselect(
            f"Select from all {len(all_categories)} categories:",
            all_categories,
            default=selected_categories if selected_categories else all_categories[:10]
        )
    
    # Display summary
    if selected_categories:
        st.success(f"✅ {len(selected_categories)} categories selected")
    else:
        st.warning("⚠️ No categories selected")
    
    return selected_categories