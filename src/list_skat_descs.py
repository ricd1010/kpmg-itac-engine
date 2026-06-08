import sys
import os
import pandas as pd

# Load SKAT
path = r"data/xinxiwang/SKAT.xls"
df = pd.read_excel(path, header=None, engine='xlrd')
print(f"--- All descriptions in {path} ---")

# Find description column (TXT50 usually)
# Row 3 seems to be header
header = df.iloc[3]
txt50_idx = -1
for i, val in enumerate(header):
    if "TXT50" in str(val):
        txt50_idx = i; break

if txt50_idx != -1:
    descs = df.iloc[4:, txt50_idx].dropna().unique().tolist()
    for d in sorted(descs):
        print(d)
else:
    print("Could not find TXT50 column.")
