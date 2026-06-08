import sys
import os
import pandas as pd

# 确保能加载到 src 目录下的模块
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

# 待测试的本地真实数据路径
targets = [
    r"data/xinxiwang/课余表-牧业生产.xls",
    r"data/xinxiwang/课余表—乳业销售.xls",
    r"data/xinxiwang/SKAT.xls"
]

print("="*50)
print("开始对本地真实 SAP 导出数据进行‘压力测试’...")
print("="*50)

for target in targets:
    if not os.path.exists(target):
        print(f"跳过不存在的文件: {target}")
        continue
        
    print(f"\n[测试对象]: {target}")
    mock = MockFile(target)
    
    # 模拟网页上传并调用核心校验逻辑
    is_v, msg, df = DataValidator.validate_file(mock, "TrialBalance" if "课余表" in target else "SKAT")
    
    if is_v:
        print(f"✅ 校验成功！结果: {msg}")
        print(f"--- 识别到的核心列名: {df.columns.tolist()}")
        print(f"--- 数据前 3 行预览:\n{df[['SAKNR', 'TXT50']].head(3) if 'TXT50' in df.columns else df.head(3)}")
    else:
        print(f"❌ 校验失败！错误: {msg}")

print("\n" + "="*50)
print("测试完毕。")
