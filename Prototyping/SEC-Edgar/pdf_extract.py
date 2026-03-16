# extract_tables_from_pdf_tabula.py
from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

PDF_PATH = Path("/Users/aakashbelide/Downloads/sec-edgar-filings/0000320193/10-K/0000320193-23-000106/full-submission.pdf")
OUT_DIR = Path("/Users/aakashbelide/Downloads/sec-edgar-filings/0000320193/10-K/0000320193-23-000106/pdf_tables_out_tabula")
CSV_DIR = OUT_DIR / "tables_csv"
XLSX_PATH = OUT_DIR / "tables.xlsx"


def extract_with_tabula(pdf_path: Path) -> List[pd.DataFrame]:
    import tabula  # type: ignore

    # lattice=True works when there are ruling lines
    # stream=True works when spacing defines columns
    dfs = tabula.read_pdf(
        str(pdf_path),
        pages="all",
        multiple_tables=True,
        lattice=True,      # try lattice first
        guess=True
    )
    return [df for df in dfs if df is not None and not df.empty]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    dfs = extract_with_tabula(PDF_PATH)
    print(f"Tabula extracted {len(dfs)} tables")

    for i, df in enumerate(dfs):
        df.to_csv(CSV_DIR / f"table_{i:03d}.csv", index=False)

    with pd.ExcelWriter(XLSX_PATH, engine="openpyxl") as writer:
        for i, df in enumerate(dfs):
            df.to_excel(writer, sheet_name=f"table_{i:03d}", index=False)

    print(f"Saved to {OUT_DIR}")


if __name__ == "__main__":
    main()