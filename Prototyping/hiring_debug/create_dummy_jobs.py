import pandas as pd
import os

# Create a dummy processed_jobs.csv for testing
data = [
    {
        "company": "JPMorganChase",
        "title": "Machine Learning Engineer",
        "description": "We use pytorch, snowflake, and databricks for our AI platform. We also use aws sagemaker.",
        "url": "http://jpm.com/job1",
        "is_ai": True,
        "categories": ["deep_learning"],
        "skills": ["pytorch", "python"],
        "posted_at": "2026-02-10"
    }
]
df = pd.DataFrame(data)
df.to_csv("/Users/aakashbelide/Aakash/Higher Studies/Course/Sem-4/DAMG 7245/Case Study 3/pe-org-air-cs3/Prototyping/hiring_debug/processed_jobs.csv", index=False)
logger.info("Created dummy processed_jobs.csv")
