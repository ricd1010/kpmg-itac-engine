import pandas as pd
import os

def check_inf_file():
    path = r"data/新希望测试数据/inf 1.XLSX"
    print(f"=== 正在分析样本文件: {path} ===")
    
    try:
        # 读取原始数据（不带表头）
        df = pd.read_excel(path, header=None)
        print("\n[前 30 行原始快照]:")
        for i, row in df.head(30).iterrows():
            print(f"Row {i:2}: {list(row.values)}")
            
    except Exception as e:
        print(f"❌ 读取失败: {str(e)}")

if __name__ == "__main__":
    check_inf_file()
