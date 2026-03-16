import pandas as pd
import os

# Create a sample jobs file to test leadership mentions and reporting lines
data = [
    {
        "company": "JPMorganChase",
        "title": "Data Scientist",
        "description": "This role reporting to Chief AI Officer will lead the adoption of generative AI models. You will work on strategic ai initiative.",
    },
    {
        "company": "Walmart",
        "title": "Head of AI", # Direct leadership title
        "description": "Leading the walmart enterprise AI transformation.",
    },
    {
        "company": "Goldman Sachs",
        "title": "AI Platform Engineer",
        "description": "Collaborates with the CAIO to define infrastructure requirements.",
    }
]
df = pd.DataFrame(data)
df.to_csv("/Users/aakashbelide/Aakash/Higher Studies/Course/Sem-4/DAMG 7245/Case Study 3/pe-org-air-cs3/Prototyping/leadership_debug/processed_jobs.csv", index=False)
print("Created sample processed_jobs.csv")
