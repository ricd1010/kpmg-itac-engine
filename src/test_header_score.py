import sys
import os
import re
import pandas as pd
import io

# Simulate the Super Splitter
def super_split(row_str):
    return [p.strip() for p in re.split(r'\t+|\s{2,}', row_str) if p.strip()]

target = r"data/xinxiwang/课余表-牧业生产.xls"
print(f"--- Analyzing Rows in {target} ---")

with open(target, 'r', encoding='utf-16') as f:
    lines = f.readlines()

for i, line in enumerate(lines[:30]):
    parts = super_split(line)
    print(f"Row {i:2} ({len(parts)} cols): {parts}")

# Score simulation
HEADER_KEYWORDS = {
    "saknr": 5, "dmbtr": 5, "konts": 5, "konth": 5, "总帐科目": 5, "总账科目": 5,
    "借方余额": 4, "贷方余额": 4, "借方金额": 4, "贷方金额": 4, "科目名称": 4, "科目描述": 4,
    "已结转余额": 4, "前一期间的余额": 4, "报表期间的贷方余额": 4, "在制表期间的借方余额": 4,
    "短文本": 2, "公司": 2, "bukrs": 5, "shkzg": 5, "txt50": 5
}
FORBIDDEN_KEYWORDS = ["时间", "制表", "筛选", "页码", "1/"]

for i, line in enumerate(lines[:30]):
    parts = super_split(line)
    row_str = " ".join(parts).lower()
    score = 0
    for fk in FORBIDDEN_KEYWORDS:
        if fk in row_str: score -= 3
    for k, weight in HEADER_KEYWORDS.items():
        if k in row_str: score += weight
    print(f"Row {i:2} Score: {score}")
