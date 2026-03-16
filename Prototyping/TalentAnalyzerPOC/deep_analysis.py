import os
import sys
import pandas as pd
import re
from collections import Counter
from typing import List, Dict, Set

# Setup path to import from current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from snowflake_client import SnowflakeClient
from dotenv import load_dotenv

# Basic stop words to avoid NLTK dependency if not installed
STOP_WORDS = {
    'and', 'the', 'to', 'of', 'a', 'in', 'for', 'with', 'on', 'is', 'at', 'by', 
    'an', 'be', 'or', 'as', 'from', 'that', 'which', 'are', 'this', 'it', 'will', 
    'not', 'have', 'has', 'can', 'but', 'into', 'all', 'more', 'about', 'their', 
    'other', 'its', 'also', 'some', 'up', 'out', 'new', 'who', 'what', 'when', 
    'where', 'why', 'how', 'our', 'we', 'your', 'you', 'my', 'me', 'us', 'they', 
    'them', 'if', 'then', 'than', 'so', 'just', 'only', 'one', 'first', 'second',
    'work', 'experience', 'year', 'years', 'role', 'team', 'business', 'job', 
    'working', 'time', 'company', 'projects', 'support', 'skills', 'knowledge',
    'ability', 'strong', 'understanding', 'using', 'based', 'development', 
    'opportunity', 'career', 'looking', 'good', 'great', 'opportunities', 
    'environment', 'people', 'culture', 'management', 'including', 'responsible',
    'required', 'preferred', 'qualification', 'qualifications', 'degree', 
    'bachelor', 'master', 'phd', 'excellent', 'communication', 'highly', 'plus',
    'proficiency', 'proficient'
}

def normalize_text(text: str) -> str:
    """Lower case and remove non-alphanumeric chars."""
    if not isinstance(text, str):
        return ""
    # Replace non-alphanumeric with space
    return re.sub(r'[^a-z0-9\s]', ' ', text.lower())

def extract_ngrams(text: str, n: int) -> List[str]:
    """Extract n-grams from text."""
    words = [w for w in normalize_text(text).split() if w not in STOP_WORDS and len(w) > 2]
    if len(words) < n:
        return []
    return [' '.join(words[i:i+n]) for i in range(len(words)-n+1)]

def analyze_titles(df: pd.DataFrame):
    """Analyze job titles to find senior/leadership patterns."""
    print("\n" + "="*50)
    print("ANALYZING JOB TITLES (Glassdoor)")
    print("="*50)
    
    titles = df['job'].dropna().tolist()
    all_words = []
    
    for title in titles:
        # Standardize
        clean_title = normalize_text(title)
        words = [w for w in clean_title.split() if w not in STOP_WORDS and len(w) > 2]
        all_words.extend(words)
        
    counts = Counter(all_words)
    
    print(f"Top 50 Frequent Terms in Titles ({len(titles)} total titles):")
    print("-" * 30)
    for word, count in counts.most_common(50):
        print(f"{word}: {count}")
    
    print("\nPotential Seniority Indicators (Manual Scan):")
    seniority_candidates = ['senior', 'lead', 'principal', 'manager', 'director', 'vp', 'chief', 'head', 'architect', 'fellow', 'staff', 'ii', 'iii', 'iv', 'v']
    for term in seniority_candidates:
        if term in counts:
            print(f"  - {term}: {counts[term]}")

def analyze_skills(descriptions: List[str]):
    """Analyze job descriptions to find skills."""
    print("\n" + "="*50)
    print("ANALYZING JOB DESCRIPTIONS (Snowflake)")
    print("="*50)
    
    ngram_counts = Counter()
    
    for desc in descriptions:
        # 1-grams (single words like 'python', 'java')
        ngram_counts.update(extract_ngrams(desc, 1))
        # 2-grams (double words like 'machine learning', 'data science')
        ngram_counts.update(extract_ngrams(desc, 2))
        # 3-grams (triple words like 'natural language processing')
        ngram_counts.update(extract_ngrams(desc, 3))
        
    print(f"Top 50 Frequent Phrases in Job Descriptions ({len(descriptions)} jobs):")
    print("-" * 30)
    
    # Heuristic: Filter for tech-sounding things (optional, but raw list is good for discovery)
    # Just show top 50
    for phrase, count in ngram_counts.most_common(50):
        print(f"{phrase}: {count}")

def main():
    # 1. Load Data
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'pe-org-air-platform', '.env'))
    if os.path.exists(env_path):
        load_dotenv(env_path)
    
    # Load JPM reviews
    csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Glassdoor review analysis', 'target_company_reviews_strict.csv'))
    
    print(f"Loading data from {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
        jpm_reviews = df[df['company_ticker'] == 'JPM'].copy()
        
        # Filter for AI/Tech manually first to focus analysis?
        # Or analyze ALL JPM titles to see what "Tech" titles exist?
        # User asked for "role names" analysis. Let's look at ALL JPM titles first to discover the tech ones.
        print(f"Found {len(jpm_reviews)} JPM reviews.")
        
        # Discover "Tech" titles by looking for tech keywords in the full dataset
        tech_keywords = ['data', 'engineer', 'developer', 'scientist', 'analyst', 'software', 'tech', 'technology', 'it', 'systems', 'network']
        pattern = '|'.join(tech_keywords)
        tech_reviews = jpm_reviews[jpm_reviews['job'].str.contains(pattern, case=False, na=False)]
        print(f"Filtered to {len(tech_reviews)} potential Tech/Data reviews for deep analysis.")
        
        analyze_titles(tech_reviews)
        
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    # Load Snowflake Data
    print("\nFetching Snowflake Data...")
    try:
        if not os.getenv("SNOWFLAKE_USER"):
            print("Skipping Snowflake (No credentials).")
            # Fallback mock for demonstration if needed, but user wants real analysis
            descriptions = [] 
        else:
            client = SnowflakeClient()
            descriptions = client.fetch_job_skills("JPM") 
            print(f"Fetched {len(descriptions)} job descriptions.")
            
            if descriptions:
                analyze_skills(descriptions)
            else:
                print("No descriptions found.")

    except Exception as e:
        print(f"Snowflake Error: {e}")

if __name__ == "__main__":
    main()
