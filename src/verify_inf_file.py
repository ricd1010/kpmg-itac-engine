import os
import sys
import pandas as pd
import io

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_validator import DataValidator

def test_inf_file():
    path = r"data/新希望测试数据/inf 1.XLSX"
    print(f"=== 开始本地样本文件 (inf 1) 解析测试 ===")
    
    if not os.path.exists(path):
        print(f"❌ 文件不存在: {path}")
        return

    try:
        with open(path, 'rb') as f:
            file_bytes = f.read()
            
        class StreamlitMockFile(io.BytesIO):
            def __init__(self, b, name):
                super().__init__(b)
                self.name = name
        
        mock_file = StreamlitMockFile(file_bytes, "inf 1.XLSX")
        
        # 运行校验逻辑 ( Samples 类型)
        is_valid, msg, df = DataValidator.validate_file(mock_file, "Samples")
        
        if is_valid:
            print(f"✅ 解析成功！")
            print(f"   检测到列名: {list(df.columns)}")
            print(f"   数据行数: {len(df)}")
            print(f"   字段映射确认:")
            if "DOC_NUM" in df.columns: print(f"      - 凭证号 (DOC_NUM): 映射成功")
            if "SAKNR" in df.columns: print(f"      - 科目 (SAKNR): 映射成功")
            if "AMOUNT" in df.columns: 
                print(f"      - 金额 (AMOUNT): 映射成功 (第一个值为: {df['AMOUNT'].iloc[0]})")
            
            print("\n[前 5 行预览]:")
            print(df.head(5)[["DOC_NUM", "SAKNR", "AMOUNT"]])
        else:
            print(f"❌ 解析失败: {msg}")
            
    except Exception as e:
        print(f"💥 测试脚本崩溃: {str(e)}")

if __name__ == "__main__":
    test_inf_file()
