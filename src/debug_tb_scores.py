import sys
import os
import pandas as pd
import re

# Ensure local src
sys.path.append(os.path.join(os.getcwd(), 'src'))

# Copy the exact logic from DataValidator
KEYWORDS = {
    "saknr": 10, "konts": 10, "konth": 10, "总帐科目": 10, "总账科目": 10,
    "dmbtr_debit": 10, "dmbtr_credit": 10, "借方余额": 10, "贷方余额": 10,
    "txt50": 5, "科目名称": 5, "科目描述": 5, "短文本": 5,
    "已结转余额": 5, "前一期间的余额": 5, "报表期间的贷方余额": 5, "在制表期间的借方余额": 5,
    "评估分组代码": 5, "科目修改": 5, "trs": 5, "valcl": 5, "帐目表": 5
}
FORBIDDEN = ["时间", "制表", "筛选", "页码", "1/", "四川", "新希望", "乳业", "琴牌", "清单", "报表"]

def debug_scoring(path):
    print(f"--- Debugging Header Scores for {path} ---")
    with open(path, 'r', encoding='utf-16') as f:
        text = f.read()
    lines = text.splitlines()
    split_data = []
    for line in lines:
        if not line.strip(): continue
        parts = [p.strip() for p in re.split(r'\t+|\s{2,}', line) if p.strip()]
        if parts: split_data.append(parts)
    
    max_cols = max(len(r) for r in split_data)
    normalized_data = [r + [None]*(max_cols-len(r)) for r in split_data]
    df_raw = pd.DataFrame(normalized_data)
    
    for i, row in df_raw.head(20).iterrows():
        row_vals = [str(v).strip().lower() for v in row.values if pd.notna(v)]
        row_str = " ".join(row_vals)
        score = 0
        for fk in FORBIDDEN:
            if fk in row_str: score -= 30
        for k, w in KEYWORDS.items():
            if k in row_str: score += w
        if len(row_vals) >= 8: score += 10
        print(f"Row {i:2}: Score={score:3} | Data={row_vals}")

path = r"data/xinxiwang/课余表-牧业生产.xls"
debug_scoring(path)
