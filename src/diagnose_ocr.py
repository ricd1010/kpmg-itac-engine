import os
import sys
import io

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ocr_processor import OCRProcessor
from llm_client import LLMClient

def diagnose_image():
    path = r"data/新希望测试数据/图片2.png"
    print(f"=== 正在深入诊断图片: {path} ===")
    
    if not os.path.exists(path):
        print("❌ 文件不存在")
        return

    try:
        with open(path, 'rb') as f:
            img_bytes = f.read()
            
        ocr = OCRProcessor()
        # 1. 获取原始 OCR 文字 (不传 LLM)
        print("\n[Step 1] 获取原始 OCR 识别文字...")
        raw_res = ocr.process_and_parse(img_bytes, llm_client=None)
        
        if "error" in raw_res:
            print(f"❌ OCR 失败: {raw_res['error']}")
            return
        
        raw_text = raw_res.get("OCR_TEXT", "")
        print("--- 原始文字开始 ---")
        print(raw_text)
        print("--- 原始文字结束 ---")

        # 2. 尝试用 AI 解析 (需配置 Key)
        print("\n[Step 2] 模拟 DeepSeek 要素提取...")
        # 此处我们通过代码模拟，如果您没有配置 Key，这里会使用 mock 逻辑
        client = LLMClient(api_key=None) # Mock mode
        final_res = ocr.process_and_parse(img_bytes, llm_client=client)
        print(f"AI 提取结果: {final_res}")

    except Exception as e:
        print(f"💥 诊断脚本崩溃: {str(e)}")

if __name__ == "__main__":
    diagnose_image()
