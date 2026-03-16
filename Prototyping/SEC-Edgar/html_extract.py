# extract_tables_from_html_robust.py
from __future__ import annotations

import re
from pathlib import Path
from io import StringIO

import pandas as pd
from bs4 import BeautifulSoup

HTML_PATH = Path("/Users/aakashbelide/Downloads/sec-edgar-filings/0000320193/10-K/0000320193-23-000106/full-submission.html")
OUT_DIR = Path("/Users/aakashbelide/Downloads/sec-edgar-filings/0000320193/10-K/0000320193-23-000106/html_tables_out")
CSV_DIR = OUT_DIR / "tables_csv"
RAW_DIR = OUT_DIR / "tables_raw_html"
XLSX_PATH = OUT_DIR / "tables.xlsx"


def sanitize_sheet_name(name: str) -> str:
    name = re.sub(r"[:\\/?*\[\]]", " ", name).strip()
    return (name[:31] if len(name) > 31 else name) or "Sheet"


def main() -> None:
    # --- basic sanity checks ---
    if not HTML_PATH.exists():
        raise FileNotFoundError(f"HTML not found: {HTML_PATH}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    html_text = HTML_PATH.read_text(encoding="utf-8", errors="ignore")
    print(f"[INFO] Loaded HTML bytes: {len(html_text):,}")
    print(f"[INFO] '<table' occurrences: {html_text.lower().count('<table')}")

    # Parse HTML and extract each table tag
    soup = BeautifulSoup(html_text, "lxml")
    table_tags = soup.find_all("table")
    print(f"[INFO] BeautifulSoup found tables: {len(table_tags)}")

    if not table_tags:
        print("[WARN] No <table> tags found. This file may not contain the primary filing HTML.")
        return

    extracted_dfs: list[pd.DataFrame] = []
    extracted_raw: list[str] = []

    for i, table in enumerate(table_tags):
        table_html = str(table)

        # Save raw table HTML no matter what (useful for debugging)
        raw_path = RAW_DIR / f"table_{i:03d}.html"
        raw_path.write_text(table_html, encoding="utf-8")
        extracted_raw.append(table_html)

        # Convert this single table into DataFrames (sometimes read_html returns multiple)
        try:
            dfs = pd.read_html(StringIO(table_html), flavor="lxml")
        except ValueError:
            # Not a parsable table
            continue
        except Exception as e:
            print(f"[WARN] Table {i:03d} parse failed: {e}")
            continue

        # Keep non-empty tables
        for df in dfs:
            # Skip tiny/empty tables
            if df is None or df.empty:
                continue
            extracted_dfs.append(df)

    print(f"[INFO] Extracted DataFrames: {len(extracted_dfs)}")

    if not extracted_dfs:
        print("[WARN] Found <table> tags but none produced DataFrames. Likely malformed/complex layout tables.")
        return

    # Save CSVs
    for j, df in enumerate(extracted_dfs):
        csv_path = CSV_DIR / f"table_{j:03d}.csv"
        df.to_csv(csv_path, index=False)
    print(f"[INFO] Saved CSV tables to: {CSV_DIR}")

    # Save Excel workbook
    with pd.ExcelWriter(XLSX_PATH, engine="openpyxl") as writer:
        for j, df in enumerate(extracted_dfs):
            sheet = sanitize_sheet_name(f"table_{j:03d}")
            df.to_excel(writer, sheet_name=sheet, index=False)
    print(f"[INFO] Saved Excel workbook: {XLSX_PATH}")


if __name__ == "__main__":
    main()