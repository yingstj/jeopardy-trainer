import pandas as pd

def load_clues(csv_path="data/all_jeopardy_clues.csv"):
    return pd.read_csv(csv_path)

def get_missed_clues(df):
    if "was_correct" not in df.columns:
        print("⚠️ Column 'was_correct' not found. Add this after quiz sessions.")
        return pd.DataFrame()
    
    missed = df[df["was_correct"] == False]
    return missed

def summarize_by_category(df):
    return df["category"].value_counts()

if __name__ == "__main__":
    df = load_clues()
    missed = get_missed_clues(df)

    if not missed.empty:
        print("\n📊 Missed Clues by Category:\n")
        print(summarize_by_category(missed))
    else:
        print("\n✅ No missed clues found or data incomplete.")
