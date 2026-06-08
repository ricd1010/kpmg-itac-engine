import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'src'))
from data_validator import DataValidator
import pandas as pd

class MockFile:
    def __init__(self, path):
        self.name = os.path.basename(path)
        with open(path, 'rb') as f:
            self.data = f.read()
    def seek(self, offset): pass
    def read(self, size=-1): return self.data
    def getvalue(self): return self.data

# Test both TB files
targets = [
    r"data/xinxiwang/课余表-牧业生产.xls",
    r"data/xinxiwang/课余表—乳业销售.xls"
]

for target in targets:
    print(f"\n=== Testing: {target} ===")
    mock = MockFile(target)
    is_v, msg, df = DataValidator.validate_file(mock, "TrialBalance")
    print(f"Validation: {is_v}")
    print(f"Message: {msg}")
    
    if not is_v:
        # Deep dive into raw reading
        df_raw = pd.read_excel(target, header=None)
        print("First 15 rows of raw data:")
        for i, row in df_raw.head(15).iterrows():
            print(f"Row {i}: {row.tolist()}")
