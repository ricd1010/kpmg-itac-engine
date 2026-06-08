import sys
import os
import pandas as pd

# 确保加载本地 src
sys.path.append(os.path.join(os.getcwd(), 'src'))
from data_validator import DataValidator

class MockFile:
    def __init__(self, path):
        self.name = os.path.basename(path)
        with open(path, 'rb') as f:
            self.data = f.read()
    def seek(self, offset): pass
    def read(self, size=-1): return self.data
    def getvalue(self): return self.data

# 针对 T030 的专项诊断
t030_targets = [
    r"data/xinxiwang/T030.xls",
    r"data/xinxiwang/T030 HEBING.xlsx"
]

print("="*60)
print("T030 专项诊断测试开启...")
print("="*60)

for target in t030_targets:
    if not os.path.exists(target):
        print(f"跳过不存在的文件: {target}")
        continue
    
    print(f"\n[测试 T030]: {target}")
    mock = MockFile(target)
    
    # 模拟网页上传
    is_v, msg, df = DataValidator.validate_file(mock, "T030")
    
    if is_v:
        print(f"✅ 成功！识别到列: {df.columns.tolist()}")
        # 检查是否包含 KONTS 或 KONTH
        has_k = "KONTS" in df.columns or "KONTH" in df.columns
        print(f"--- 关键列匹配结果: {'OK' if has_k else 'FAIL (Missing KONTS/KONTH)'}")
        print(df.head(3))
    else:
        print(f"❌ 失败！报错信息: {msg}")
        # 如果彻底失败，尝试探测二进制特征
        with open(target, 'rb') as f:
            head = f.read(16)
            print(f"--- 文件头 16 字节 (Hex): {head.hex(' ')}")

print("\n" + "="*60)
