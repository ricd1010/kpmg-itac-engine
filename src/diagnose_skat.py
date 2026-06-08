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

target = r"data/xinxiwang/SKAT.xls"
mock = MockFile(target)
is_v, msg, df = DataValidator.validate_file(mock, "SKAT")

print(f"Validation Result: {is_v}")
print(f"Message: {msg}")
if df is not None:
    print(f"Shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    print("Head:")
    print(df.head())
else:
    # Diagnostic: Read directly and see what find_real_header does
    df_raw = pd.read_excel(target, header=None)
    print(f"Raw Shape: {df_raw.shape}")
    print("Raw Head:")
    print(df_raw.head(10))
