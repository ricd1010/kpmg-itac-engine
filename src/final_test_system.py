import os
import sys
import numpy as np
from PIL import Image
import io

# 确保能导入 src 目录下的模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_full_system():
    print("=== ITAC 自动化底稿系统 全链路压力测试 ===")
    
    # 1. 测试 OCR 引擎初始化 (针对之前的 PIR 报错)
    print("\n[Step 1] 初始化本地 OCR 引擎...")
    try:
        from ocr_processor import OCRProcessor
        ocr = OCRProcessor()
        print("✅ OCR 引擎初始化成功！")
    except Exception as e:
        print(f"❌ OCR 引擎初始化失败: {str(e)}")
        return

    # 2. 测试 OCR 识别逻辑 (模拟图片)
    print("\n[Step 2] 测试图片识别与可视化...")
    try:
        # 创建一个带有文字的空白图片进行测试
        dummy_img = Image.new('RGB', (200, 100), color=(255, 255, 255))
        img_byte_arr = io.BytesIO()
        dummy_img.save(img_byte_arr, format='JPEG')
        
        # 运行识别
        res = ocr.process_and_parse(img_byte_arr.getvalue())
        
        if "error" in res:
            print(f"❌ OCR 运行故障: {res['error']}")
            if "tip" in res: print(f"💡 建议: {res['tip']}")
        else:
            print("✅ OCR 识别逻辑跑通！")
            if "viz_img" in res:
                print("✅ 结果可视化 (红框图) 生成成功！")
    except Exception as e:
        print(f"❌ OCR 识别阶段崩溃: {str(e)}")

    # 3. 测试 DeepSeek 集成与底稿生成
    print("\n[Step 3] 测试 DeepSeek 审计逻辑生成...")
    try:
        from llm_client import LLMClient
        # 使用 mock 模式测试逻辑流
        client = LLMClient(api_key=None) 
        
        from core2_main import Core2Orchestrator
        data_dir = r"C:\Users\Laptop\.gemini\tmp\system32\AuditHackathon\data"
        if not os.path.exists(data_dir): os.makedirs(data_dir)
        
        c2 = Core2Orchestrator(data_dir)
        c2.llm_client = client
        
        mock_scenarios = [{"name": "2.2.1 采购收货", "total_value": 100000, "accounts": ["140301"]}]
        audit_context = {
            "entity_name": "测试单位",
            "system_name": "SAP",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31"
        }
        
        results = c2.generate_di_descriptions(mock_scenarios, audit_context)
        print(f"✅ AI 描述生成成功！(示例长度: {len(results[0]['di_description'])} 字)")
        
        # 4. 测试 Excel 导出 (标准化模板)
        print("\n[Step 4] 测试标准化 Excel 导出...")
        from report_generator import ReportGenerator
        gen = ReportGenerator(data_dir)
        path = gen.generate(mock_scenarios, results, audit_context)
        print(f"✅ 标准化底稿已生成至: {path}")
        
    except Exception as e:
        print(f"❌ 审计逻辑/导出阶段故障: {str(e)}")

    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_full_system()
