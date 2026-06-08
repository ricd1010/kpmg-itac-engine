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

target = r"data/xinxiwang/课余表-牧业生产.xls"
print(f"=== Deep Inspecting: {target} ===")

# Try reading with xlrd
try:
    df = pd.read_excel(target, header=None, engine='xlrd')
    print("Successfully read with xlrd.")
    for i, row in df.head(20).iterrows():
        print(f"Row {i:2}: {row.tolist()}")
except Exception as e:
    print(f"Failed to read with xlrd: {e}")
    # Try as text
    with open(target, 'r', encoding='latin1', errors='ignore') as f:
        print("First 500 chars of raw text:")
        print(f.read(500))
