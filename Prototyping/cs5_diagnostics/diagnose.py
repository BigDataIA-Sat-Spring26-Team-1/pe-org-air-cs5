"""
CS5 Portfolio Data Discrepancy Diagnostics — Direct Snowflake Edition
=====================================================================
Tables found: ASSESSMENTS, COMPANIES, COMPANY_SIGNAL_SUMMARIES, CULTURE_SCORES,
              DIMENSION_SCORES, DOCUMENTS, DOCUMENT_CHUNKS, EXTERNAL_SIGNALS,
              GLASSDOOR_REVIEWS, INDUSTRIES, SIGNAL_EVIDENCE

Run from the Prototyping folder:
    uv run python cs5_diagnostics/diagnose.py
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import snowflake.connector
import pandas as pd

platform_env = Path(__file__).parent.parent.parent / "pe-org-air-platform" / ".env"
proto_env    = Path(__file__).parent.parent / ".env"
load_dotenv(platform_env if platform_env.exists() else proto_env, override=True)

TICKERS = ["NVDA", "JPM", "WMT", "GE", "DG", "CAT"]


def connect():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        role=os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    )


def q(cur, sql, params=None):
    cur.execute(sql, params or [])
    cols = [d[0].lower() for d in cur.description]
    return pd.DataFrame(cur.fetchall(), columns=cols)


def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def show_columns(cur, table):
    try:
        df = q(cur, f"SHOW COLUMNS IN TABLE {table}")
        col_col = next((c for c in df.columns if "column_name" in c), df.columns[2])
        return df[col_col].tolist()
    except Exception as e:
        return [f"ERROR: {e}"]


# ──────────────────────────────────────────────────────────────────────────────
# 1. SCHEMA EXPLORATION
# ──────────────────────────────────────────────────────────────────────────────
def check_schema(cur):
    section("1. TABLE SCHEMAS — all column names")
    for table in ("COMPANIES", "ASSESSMENTS", "DIMENSION_SCORES",
                  "SIGNAL_EVIDENCE", "COMPANY_SIGNAL_SUMMARIES"):
        cols = show_columns(cur, table)
        print(f"\n  {table}: {cols}")


# ──────────────────────────────────────────────────────────────────────────────
# 2. COMPANIES — what fields exist for sector?
# ──────────────────────────────────────────────────────────────────────────────
def check_companies(cur):
    section("2. COMPANIES TABLE — first 10 rows (all columns)")
    df = q(cur, "SELECT * FROM companies LIMIT 10")
    print(df.to_string(index=False))

    print("\n  Tickers in DB:")
    df2 = q(cur, "SELECT id, ticker, name FROM companies WHERE ticker IN ('NVDA','JPM','WMT','GE','DG','CAT') ORDER BY ticker")
    print(df2.to_string(index=False))


# ──────────────────────────────────────────────────────────────────────────────
# 3. ASSESSMENTS — score fields, confidence, dimension_scores column
# ──────────────────────────────────────────────────────────────────────────────
def check_assessments(cur):
    section("3. ASSESSMENTS — latest per ticker")

    # Get company IDs for our tickers
    print("\n  Latest assessment per company:")
    df = q(cur, """
        SELECT c.ticker,
               a.org_air_score, a.v_r_score, a.h_r_score, a.synergy_score,
               a.confidence_lower, a.confidence_upper, a.confidence_score,
               a.assessment_type, a.created_at
        FROM assessments a
        JOIN companies c ON c.id = a.company_id
        WHERE c.ticker IN ('NVDA','JPM','WMT','GE','DG','CAT')
        ORDER BY c.ticker, a.created_at DESC
    """)
    # Take first (latest) per ticker
    latest = df.groupby("ticker").first().reset_index()
    print(latest.to_string(index=False))

    # Check if dimension_scores is a column
    cols = show_columns(cur, "ASSESSMENTS")
    has_dim_col = any("dimension_score" in c.lower() for c in cols)
    print(f"\n  'dimension_scores' JSON column in ASSESSMENTS: {has_dim_col}")

    if has_dim_col:
        try:
            sample = q(cur, """
                SELECT a.dimension_scores
                FROM assessments a JOIN companies c ON c.id=a.company_id
                WHERE c.ticker='NVDA' ORDER BY a.created_at DESC LIMIT 1
            """)
            print(f"  Value: {repr(sample.iloc[0,0])[:500]}")
        except Exception as e:
            print(f"  Error reading it: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# 4. DIMENSION_SCORES TABLE
# ──────────────────────────────────────────────────────────────────────────────
def check_dimension_scores(cur):
    section("4. DIMENSION_SCORES TABLE — per ticker")

    cols = show_columns(cur, "DIMENSION_SCORES")
    print(f"  Columns: {cols}")

    df = q(cur, """
        SELECT c.ticker, ds.dimension, ds.score, ds.evidence_count
        FROM dimension_scores ds
        JOIN assessments a ON a.id = ds.assessment_id
        JOIN companies c ON c.id = a.company_id
        WHERE c.ticker IN ('NVDA','DG')
        ORDER BY c.ticker, ds.dimension
        LIMIT 30
    """)
    print(df.to_string(index=False))

    print("\n  Distinct dimension values in DB:")
    dims = q(cur, "SELECT DISTINCT dimension FROM dimension_scores ORDER BY dimension")
    print("  " + ", ".join(dims["dimension"].tolist()))


# ──────────────────────────────────────────────────────────────────────────────
# 5. SIGNAL_EVIDENCE — total counts (no limit)
# ──────────────────────────────────────────────────────────────────────────────
def check_signal_evidence(cur):
    section("5. SIGNAL_EVIDENCE — total counts per ticker (no cap)")

    cols = show_columns(cur, "SIGNAL_EVIDENCE")
    print(f"  SIGNAL_EVIDENCE columns: {cols}")

    # Try join via signal_id → signals (if that table exists)
    # From SHOW TABLES we have: SIGNAL_EVIDENCE but not SIGNALS separately
    # Maybe signal_evidence has a direct ticker or company_id col

    # Count via whatever join makes sense
    # First try: join via signal_id
    try:
        df = q(cur, """
            SELECT c.ticker, COUNT(*) AS evidence_count
            FROM signal_evidence se
            JOIN companies c ON c.id = se.company_id
            WHERE c.ticker IN ('NVDA','JPM','WMT','GE','DG','CAT')
            GROUP BY c.ticker ORDER BY c.ticker
        """)
        print("\n  Counts via company_id:")
        print(df.to_string(index=False))
    except Exception as e:
        print(f"  No company_id on signal_evidence: {e}")
        # Try via signal_id → look for a signals table or other FK
        try:
            df = q(cur, """
                SELECT c.ticker, COUNT(*) AS evidence_count
                FROM signal_evidence se
                JOIN external_signals es ON es.id = se.signal_id
                JOIN companies c ON c.id = es.company_id
                WHERE c.ticker IN ('NVDA','JPM','WMT','GE','DG','CAT')
                GROUP BY c.ticker ORDER BY c.ticker
            """)
            print("\n  Counts via external_signals:")
            print(df.to_string(index=False))
        except Exception as e2:
            print(f"  Via external_signals failed: {e2}")

    # Sample rows from signal_evidence
    print("\n  First 3 rows of signal_evidence (all columns):")
    sample = q(cur, "SELECT * FROM signal_evidence LIMIT 3")
    print(sample.to_string(index=False))


# ──────────────────────────────────────────────────────────────────────────────
# 6. COMPANY_SIGNAL_SUMMARIES — probably has the total count
# ──────────────────────────────────────────────────────────────────────────────
def check_signal_summaries(cur):
    section("6. COMPANY_SIGNAL_SUMMARIES — aggregate counts")
    cols = show_columns(cur, "COMPANY_SIGNAL_SUMMARIES")
    print(f"  Columns: {cols}")

    df = q(cur, """
        SELECT c.ticker, css.*
        FROM company_signal_summaries css
        JOIN companies c ON c.id = css.company_id
        WHERE c.ticker IN ('NVDA','JPM','WMT','GE','DG','CAT')
        ORDER BY c.ticker
    """)
    print(df.to_string(index=False))


# ──────────────────────────────────────────────────────────────────────────────
# 7. ENTRY SCORE — how many assessments exist per company
# ──────────────────────────────────────────────────────────────────────────────
def check_entry_score(cur):
    section("7. ENTRY SCORE — assessment count and oldest vs latest per ticker")
    df = q(cur, """
        SELECT c.ticker,
               COUNT(*) AS count,
               MIN(a.org_air_score) AS min_score,
               MAX(a.org_air_score) AS max_score,
               MIN(a.created_at) AS oldest,
               MAX(a.created_at) AS newest
        FROM assessments a
        JOIN companies c ON c.id = a.company_id
        WHERE c.ticker IN ('NVDA','JPM','WMT','GE','DG','CAT')
        GROUP BY c.ticker
        ORDER BY c.ticker
    """)
    print(df.to_string(index=False))

    print("\n  NVDA all assessments (ordered oldest first):")
    df2 = q(cur, """
        SELECT a.org_air_score, a.assessment_type, a.assessment_date, a.created_at
        FROM assessments a
        JOIN companies c ON c.id = a.company_id
        WHERE c.ticker = 'NVDA'
        ORDER BY a.created_at ASC
    """)
    print(df2.to_string(index=False))


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
def main():
    print("CS5 Diagnostics — Direct Snowflake Queries")
    print(f"Account: {os.environ['SNOWFLAKE_ACCOUNT']}  DB: {os.environ['SNOWFLAKE_DATABASE']}")

    conn = connect()
    cur = conn.cursor()
    try:
        check_schema(cur)
        check_companies(cur)
        check_assessments(cur)
        check_dimension_scores(cur)
        check_signal_evidence(cur)
        check_signal_summaries(cur)
        check_entry_score(cur)
    except Exception as e:
        import traceback
        print(f"\nFATAL: {e}")
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

    print("\n" + "="*70)
    print("  Diagnostics complete.")
    print("="*70)


if __name__ == "__main__":
    main()
