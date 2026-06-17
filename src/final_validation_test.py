import sys
import os
import pandas as pd
import io

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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

# 定义所有真实测试用例
test_cases = [
    {"path": r"data/xinxiwang/T030.xls", "type": "T030"},
    {"path": r"data/xinxiwang/T030 HEBING.xlsx", "type": "T030"},
    {"path": r"data/xinxiwang/SKAT.xls", "type": "SKAT"},
    {"path": r"data/xinxiwang/课余表-牧业生产.xls", "type": "TrialBalance"},
    {"path": r"data/xinxiwang/课余表—乳业销售.xls", "type": "TrialBalance"}
]

print("="*70)
print(f"{'文件名称':<30} | {'类型':<12} | {'状态':<10}")
print("-"*70)

all_pass = True
for case in test_cases:
    if not os.path.exists(case["path"]):
        print(f"{case['path']:<30} | {case['type']:<12} | ⚠️ 文件不存在")
        continue
        
    mock = MockFile(case["path"])
    try:
        is_v, msg, df = DataValidator.validate_file(mock, case["type"])
        status = "✅ 通过" if is_v else "❌ 失败"
        print(f"{os.path.basename(case['path']):<30} | {case['type']:<12} | {status}")
        if not is_v:
            print(f"   └─ 原因: {msg}")
            all_pass = False
    except Exception as e:
        print(f"{os.path.basename(case['path']):<30} | {case['type']:<12} | 💥 崩溃")
        print(f"   └─ 异常: {str(e)}")
        all_pass = False

print("-"*70)
if all_pass:
    print("🎉 所有关键文件类型全部通过本地压力测试！")
else:
    print("⚠️ 部分文件仍未通过，请检查逻辑。")
print("="*70)
