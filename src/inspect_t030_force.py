import sys
import os
import pandas as pd

# 强制使用特定引擎读取并查看前 10 行
target = r"data/xinxiwang/T030.xls"
print(f"--- 强制读取 {target} ---")
try:
    df = pd.read_excel(target, header=None, engine='xlrd')
    for i, row in df.head(10).iterrows():
        print(f"Row {i:2}: {row.tolist()}")
except Exception as e:
    print(f"读取失败: {e}")

target2 = r"data/xinxiwang/T030 HEBING.xlsx"
print(f"\n--- 强制读取 {target2} ---")
try:
    df = pd.read_excel(target2, header=None, engine='openpyxl')
    for i, row in df.head(10).iterrows():
        print(f"Row {i:2}: {row.tolist()}")
except Exception as e:
    print(f"读取失败: {e}")
