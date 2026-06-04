import pandas as pd
import io

path = r"data/新希望测试数据/课余表-牧业生产.xls"

print("--- 尝试手动解析测试 ---")

try:
    with open(path, 'rb') as f:
        content = f.read()
    
    # 尝试 UTF-16 解码
    text_content = content.decode('utf-16')
    print("✅ UTF-16 解码成功")
    
    # 使用正则表达式分隔符尝试读取
    # 报表格式通常有连续空格
    df = pd.read_csv(io.StringIO(text_content), sep=r'\s{2,}', engine='python', header=None)
    print("✅ pd.read_csv (regex-space) 成功")
    print(f"   Shape: {df.shape}")
    print(f"   Columns: {df.columns.tolist()}")
    print("   Data preview:")
    print(df.head(10))

except Exception as e:
    print(f"❌ 手动解析失败: {str(e)}")
