import pandas as pd
import os

target = r"data/xinxiwang/T030 HEBING.xlsx"
print(f"--- Targeted Test: {target} ---")

try:
    # Test 1: Simple read
    df = pd.read_excel(target, header=None)
    print(f"Read success. Shape: {df.shape}")
    print("Row 0:", df.iloc[0].tolist())
    
    # Test 2: Scoring
    HEADER_KEYWORDS = {
        "saknr": 5, "dmbtr": 5, "konts": 5, "konth": 5, "总帐科目": 5, "总账科目": 5,
        "评估分组代码": 5, "科目修改": 5, "trs": 5, "valcl": 5, "帐目表": 5
    }
    
    row0 = df.iloc[0]
    vals = [str(v).strip().lower() for v in row0.values if pd.notna(v) and str(v).strip()]
    row_str = " ".join(vals)
    score = 0
    for k, weight in HEADER_KEYWORDS.items():
        if k in row_str:
            score += weight
            print(f"Matched '{k}' (+{weight})")
    print(f"Total Score for Row 0: {score}")

except Exception as e:
    print(f"FAILED: {e}")
