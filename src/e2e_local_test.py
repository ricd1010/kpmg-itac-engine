import os
import sys
import pandas as pd
import io

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_validator import DataValidator
from core1_main import Core1Orchestrator
from core2_main import Core2Orchestrator
from report_generator import ReportGenerator

def e2e_test():
    base_dir = r"data/新希望测试数据"
    temp_dir = r"data/test_run"
    if not os.path.exists(temp_dir): os.makedirs(temp_dir)
    
    files = {
        "SKAT": "SKAT.xls",
        "T030": "T030 HEBING.xlsx",
        "TrialBalance": "课余表-牧业生产.xls",
        "Samples": "inf 1.XLSX"
    }
    
    print("=== 开始本地文件全链路 E2E 测试 ===")
    
    validated_dfs = {}
    
    # 1. 模拟上传与校验
    for f_type, f_name in files.items():
        path = os.path.join(base_dir, f_name)
        print(f"   正在处理: {f_type} -> {f_name}")
        with open(path, 'rb') as f: fb = f.read()
        
        class SF(io.BytesIO):
            def __init__(self, b, n): super().__init__(b); self.name = n
        
        is_v, msg, df = DataValidator.validate_file(SF(fb, f_name), f_type)
        if not is_v:
            print(f"❌ {f_type} 校验失败: {msg}")
            return
        validated_dfs[f_type] = df
        df.to_csv(os.path.join(temp_dir, f"{f_type}.csv"), index=False, encoding='utf-8-sig')

    print("✅ 所有文件校验并通过预处理")

    # 2. 运行场景识别 (Core 1)
    c1 = Core1Orchestrator(temp_dir)
    ranked = c1.run()
    print(f"✅ Core 1 运行完成，识别到 {len(ranked)} 个场景")
    for r in ranked: print(f"      - {r['name']}")

    # 3. 运行 D&I 生成 (Core 2)
    print("\n   正在运行 Core 2 (D&I 生成)...")
    c2 = Core2Orchestrator(temp_dir)
    audit_context = {"entity_name": "新希望本地测试", "system_name": "SAP"}
    
    try:
        di_results = c2.generate_di_descriptions(ranked, audit_context)
        print(f"✅ Core 2 运行完成，成功为 {len(di_results)} 个场景匹配了样本并生成描述")
    except Exception as e:
        print(f"❌ Core 2 运行崩溃: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # 4. 运行报表生成
    gen = ReportGenerator(temp_dir)
    path = gen.generate(ranked, di_results, audit_context)
    print(f"✅ 最终底稿已生成: {path}")

if __name__ == "__main__":
    e2e_test()
