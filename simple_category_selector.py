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
    Note: Jeopardy has 57,000+ unique categories that have appeared over the years
    """
    all_categories = sorted(df["category"].unique())
    total_categories = len(all_categories)
    
    # Calculate category frequencies (how often each category appears)
    category_counts = df['category'].value_counts()
    
    st.markdown("### 📚 Jeopardy Category Selection")
    st.caption(f"Choose from {total_categories:,} unique Jeopardy categories")
    
    selection_mode = st.radio(
        "How would you like to select categories?",
        ["🎯 Most Common Categories", "🔍 Search Categories", "🎲 Random Mix", "📝 Browse All"],
        horizontal=False
    )
    
    selected_categories = []
    
    if selection_mode == "🎯 Most Common Categories":
        st.info("📊 Select categories that appear most frequently in Jeopardy history")
        
        preset = st.selectbox(
            "Number of categories to include:",
            [
                "Top 50 Categories (Quick Game)",
                "Top 100 Categories (Standard)", 
                "Top 250 Categories (Extended)",
                "Top 500 Categories (Comprehensive)",
                "Top 1000 Categories (Marathon)"
            ],
            index=1  # Default to Top 100
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
        st.success(f"✅ Selected the {len(selected_categories)} most frequently appearing categories")
        with st.expander(f"Preview selected categories (showing first 30)"):
            # Show in columns
            cols = st.columns(3)
            for i, cat in enumerate(selected_categories[:30]):
                count = category_counts[cat]
                cols[i % 3].write(f"• {cat} ({count} clues)")
            if len(selected_categories) > 30:
                st.write(f"... plus {len(selected_categories) - 30} more categories")
    
    elif selection_mode == "🔍 Search Categories":
        st.info("🔎 Search through all 57,000+ Jeopardy categories by keyword")
        
        # Search functionality
        search_term = st.text_input(
            "Enter search term:",
            placeholder="e.g., 'HISTORY', 'SCIENCE', 'MOVIES', 'SHAKESPEARE'",
            help="Search is case-insensitive"
        )
        
        if search_term:
            # Filter categories by search term
            filtered = [cat for cat in all_categories if search_term.lower() in cat.lower()]
            
            if filtered:
                st.success(f"Found {len(filtered)} categories containing '{search_term}'")
                
                # Option to select all or choose specific ones
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Use All Matches", use_container_width=True, type="primary"):
                        selected_categories = filtered
                with col2:
                    if st.button("🔄 Clear Selection", use_container_width=True):
                        selected_categories = []
                
                # Manual selection from filtered
                selected_categories = st.multiselect(
                    f"Or select specific categories from the {len(filtered)} matches:",
                    filtered,
                    default=filtered[:min(20, len(filtered))],
                    help="Showing up to 20 by default, you can add/remove as needed"
                )
            else:
                st.warning(f"No categories found containing '{search_term}'")
        else:
            st.info("💡 Try searching for: HISTORY, SCIENCE, LITERATURE, MOVIES, SPORTS, etc.")
    
    elif selection_mode == "🎲 Random Mix":
        st.info("🎲 Get a random selection of categories for variety")
        
        num_random = st.slider(
            "How many random categories?",
            min_value=10,
            max_value=500,
            value=100,
            step=10,
            help="Random selection from all 57,000+ categories"
        )
        
        if st.button("🎲 Generate Random Selection", type="primary", use_container_width=True):
            selected_categories = random.sample(all_categories, min(num_random, len(all_categories)))
            st.session_state.random_categories = selected_categories
            st.success(f"✅ Randomly selected {len(selected_categories)} categories")
        
        # Show current selection if any
        if 'random_categories' in st.session_state:
            selected_categories = st.session_state.random_categories
            with st.expander(f"Preview your {len(selected_categories)} random categories"):
                cols = st.columns(3)
                for i, cat in enumerate(selected_categories[:30]):
                    cols[i % 3].write(f"• {cat}")
                if len(selected_categories) > 30:
                    st.write(f"... plus {len(selected_categories) - 30} more")
    
    else:  # Browse All
        st.info(f"📝 Browse and select from all {total_categories:,} Jeopardy categories")
        
        # Provide some quick filters
        st.write("**Quick filters to help find categories:**")
        
        col1, col2, col3 = st.columns(3)
        
        filters_applied = []
        with col1:
            if st.checkbox("📜 History-related"):
                filtered = [c for c in all_categories if 'HISTORY' in c.upper()]
                selected_categories.extend(filtered)
                filters_applied.append(f"History ({len(filtered)})")
        
        with col2:
            if st.checkbox("🔬 Science-related"):
                filtered = [c for c in all_categories if 'SCIENCE' in c.upper()]
                selected_categories.extend(filtered)
                filters_applied.append(f"Science ({len(filtered)})")
        
        with col3:
            if st.checkbox("🎬 Entertainment"):
                filtered = [c for c in all_categories if any(word in c.upper() for word in ['MOVIE', 'TV', 'FILM'])]
                selected_categories.extend(filtered)
                filters_applied.append(f"Entertainment ({len(filtered)})")
        
        # Remove duplicates
        selected_categories = list(set(selected_categories))
        
        if filters_applied:
            st.caption(f"Filters applied: {', '.join(filters_applied)}")
        
        # Manual multiselect
        selected_categories = st.multiselect(
            f"Select categories (showing filtered results):" if selected_categories else f"Browse all {total_categories:,} categories:",
            all_categories,
            default=selected_categories if selected_categories else all_categories[:10],
            help="Start typing to search, or scroll to browse"
        )
    
    # Display summary
    if selected_categories:
        st.success(f"✅ {len(selected_categories)} categories selected")
    else:
        st.warning("⚠️ No categories selected")
    
    return selected_categories