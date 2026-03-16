# Glassdoor Pipeline Validation Scripts

This directory contains standalone scripts used to verify the Glassdoor data pipeline end-to-end.

## Scripts

1.  **`verify_glassdoor_pipeline.py`**
    - Runs the `GlassdoorOrchestrator` for a single company (default: `NVDA`).
    - Verifies S3 caching logic.
    - Verifies Snowflake data insertion (Reviews & Culture Scores).

2.  **`setup_glassdoor_tables.py`**
    - [Optional] Creates the necessary tables (`glassdoor_reviews`, `culture_scores`) in Snowflake if they don't exist.
    - *Note:* The main pipeline now includes this logic automatically, but this script remains for manual setup/testing.

## How to Run

These scripts depend on the main application code in `pe-org-air-platform`. You must run them from the root of that project so python can find the `app` module.

**Prerequisites:**
- Ensure you have `poetry` installed.
- Ensure your `.env` file is set up in `pe-org-air-platform/.env`.

**Command:**
From the `pe-org-air-platform` directory:

```bash
# 1. Setup Tables (Optional)
poetry run python ../Prototyping/glassdoor_pipeline_validation/setup_glassdoor_tables.py

# 2. Verify Pipeline
poetry run python ../Prototyping/glassdoor_pipeline_validation/verify_glassdoor_pipeline.py
```

*Note: You may need to adjust `sys.path` in the scripts if you run them differently, but running via `poetry run python path/to/script.py` from the project root is the most reliable method.*
