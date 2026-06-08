import sys
import os
import pandas as pd

# Path to session TrialBalance (which was cleaned)
path = r"data/sessions/test_8fd31796/TrialBalance.csv"
if os.path.exists(path):
    df = pd.read_csv(path)
    print(f"--- All descriptions in {path} ---")
    if 'TXT50' in df.columns:
        descs = df['TXT50'].dropna().unique().tolist()
        for d in sorted(descs):
            print(d)
    else:
        print(f"TXT50 not in columns: {df.columns.tolist()}")
else:
    print(f"Path not found: {path}")
