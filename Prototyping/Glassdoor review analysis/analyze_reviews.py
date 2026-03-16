import pandas as pd

def main():
    # Read the CSV file
    print("Loading CSV file...")
    csv_path = '/Users/aakashbelide/Aakash/Higher Studies/Course/Sem-4/DAMG 7245/Case Study 3/pe-org-air-cs3/all_reviews.csv'
    df = pd.read_csv(csv_path)
    
    # Print column names
    print('\n' + '=' * 70)
    print('COLUMN NAMES:')
    print('=' * 70)
    for i, col in enumerate(df.columns, 1):
        print(f'{i:2d}. {col}')
    
    print('\n' + '=' * 70)
    print(f'Total rows: {len(df):,}')
    print(f'Total columns: {len(df.columns)}')
    print('=' * 70)
    
    # Display first few rows to understand the data structure
    print('\n' + '=' * 70)
    print('SAMPLE DATA (First 5 rows):')
    print('=' * 70)
    print(df.head().to_string())
    
    # Display data types
    print('\n' + '=' * 70)
    print('DATA TYPES:')
    print('=' * 70)
    print(df.dtypes)
    
    # Check for company-related columns
    print('\n' + '=' * 70)
    print('CHECKING FOR COMPANY-RELATED COLUMNS:')
    print('=' * 70)
    company_related_cols = [col for col in df.columns if 'company' in col.lower() 
                           or 'firm' in col.lower() 
                           or 'employer' in col.lower()
                           or 'organization' in col.lower()
                           or 'ticker' in col.lower()
                           or 'symbol' in col.lower()]
    
    if company_related_cols:
        print(f"Found {len(company_related_cols)} company-related columns:")
        for col in company_related_cols:
            print(f"  - {col}")
            # Show unique values if not too many
            unique_count = df[col].nunique()
            print(f"    Unique values: {unique_count}")
            if unique_count <= 20:
                print(f"    Values: {df[col].unique()[:20].tolist()}")
            else:
                print(f"    Sample values: {df[col].dropna().unique()[:10].tolist()}")
    else:
        print("No obvious company-related columns found.")
        print("\nShowing sample values from all columns to help identify company data:")
        for col in df.columns:
            print(f"\n{col}:")
            print(f"  Sample values: {df[col].dropna().head(3).tolist()}")

if __name__ == "__main__":
    main()
