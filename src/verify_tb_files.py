import os
import sys
import pandas as pd

# Add the current script's parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_validator import DataValidator

class MockFile:
    def __init__(self, path):
        self.name = os.path.basename(path)
        with open(path, 'rb') as f:
            self.content = f.read()
    def getvalue(self):
        return self.content
    def seek(self, pos):
        pass # Simple mock, pandas handles the bytes object or I'll pass io.BytesIO

def test_local_files():
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "xinxiwang")
    files = ["课余表-牧业生产.xls", "课余表—乳业销售.xls"]
    
    print("=== 开始本地科余表解析测试 ===")
    
    for f_name in files:
        path = os.path.join(base_dir, f_name)
        print(f"\n正在测试文件: {f_name}")
        
        try:
            # We need to simulate the file object Streamlit provides
            import io
            with open(path, 'rb') as f:
                file_bytes = f.read()
                
            # Create a class that mimics streamlit's UploadedFile
            class StreamlitMockFile(io.BytesIO):
                def __init__(self, b, name):
                    super().__init__(b)
                    self.name = name
            
            mock_file = StreamlitMockFile(file_bytes, f_name)
            
            is_valid, msg, df = DataValidator.validate_file(mock_file, "TrialBalance")
            
            if is_valid:
                print(f"✅ 解析成功！")
                print(f"   检测到列名: {list(df.columns)}")
                print(f"   数据行数: {len(df)}")
                print(f"   首行预览: {df.iloc[0].to_dict()}")
            else:
                print(f"❌ 解析失败: {msg}")
                
        except Exception as e:
            print(f"💥 测试脚本崩溃: {str(e)}")

if __name__ == "__main__":
    test_local_files()
