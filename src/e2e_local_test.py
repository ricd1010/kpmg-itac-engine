import sys
import os
import pandas as pd
import uuid
import shutil

# Ensure local src is in path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from data_validator import DataValidator
from core1_main import Core1Orchestrator
from core2_main import Core2Orchestrator
from report_generator import ReportGenerator

def run_e2e_test():
    print("="*60)
    print("🚀 开始本地全链路 E2E 自动化测试...")
    print("="*60)

    # 1. Setup Session Environment
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    base_dir = os.getcwd()
    session_dir = os.path.join(base_dir, "data", "sessions", session_id)
    os.makedirs(session_dir, exist_ok=True)
    print(f"[1/5] 创建测试沙箱: {session_dir}")

    # 2. Simulate File Upload & Validation
    raw_data_map = {
        "T030": os.path.join(base_dir, "data", "xinxiwang", "T030 HEBING.xlsx"),
        "SKAT": os.path.join(base_dir, "data", "xinxiwang", "SKAT.xls"),
        "TrialBalance": os.path.join(base_dir, "data", "xinxiwang", "课余表-牧业生产.xls")
    }

    class MockFile:
        def __init__(self, path):
            self.name = os.path.basename(path)
            with open(path, 'rb') as f: self.content = f.read()
        def seek(self, pos): pass
        def read(self, size=-1): return self.content
        def getvalue(self): return self.content

    print("[2/5] 执行数据校验与清洗...")
    for f_type, f_path in raw_data_map.items():
        mock = MockFile(f_path)
        is_v, msg, df = DataValidator.validate_file(mock, f_type)
        if not is_v:
            print(f"❌ {f_type} 校验失败: {msg}")
            return False
        # Save to session dir
        df.to_csv(os.path.join(session_dir, f"{f_type}.csv"), index=False, encoding='utf-8-sig')
        print(f"   ✅ {f_type} 已就绪 ({df.shape[0]} 行)")

    # 3. Core 1: Scenario Identification
    print("[3/5] 核心引擎 1: 场景识别与重要性排序...")
    c1 = Core1Orchestrator(session_dir)
    account_roles = c1.mapper.load_and_classify()
    print(f"   - 原始分类科目数: {len(account_roles)}")
    
    c1.verifier.load_configs()
    print(f"   - T030 配置科目数: {len(c1.verifier.configured_accounts)}")
    
    verified_roles = c1.verifier.verify(account_roles)
    print(f"   - T030 验证通过科目数: {len(verified_roles)}")

    ranked = c1.run()
    
    if not ranked:
        print("❌ Core1 失败: 未能识别出任何审计场景。")
        return False
    
    total_materiality = sum(r['total_value'] for r in ranked)
    print(f"   ✅ 识别出 {len(ranked)} 个场景，总重要性金额: {total_materiality:,.2f}")
    if total_materiality == 0:
        print("❌ 逻辑报警: 重要性金额全为 0，请检查科目匹配逻辑！")
        return False

    # 4. Core 2: D&I Narrative Generation (Mocking LLM to save time/cost)
    print("[4/5] 核心引擎 2: 样本合成与 D&I 描述...")
    # Mocking Samples.csv first (mimic OCR results)
    sample_data = [
        {"DOC_NUM": "10001", "SAKNR": "1002010201", "TXT50": "农业银行", "AMOUNT": 1234.56, "SHKZG": "S", "DATE": "2026-06-01"},
        {"DOC_NUM": "10001", "SAKNR": "2202010101", "TXT50": "应付账款", "AMOUNT": 1234.56, "SHKZG": "H", "DATE": "2026-06-01"}
    ]
    pd.DataFrame(sample_data).to_csv(os.path.join(session_dir, "Samples.csv"), index=False, encoding='utf-8-sig')
    
    c2 = Core2Orchestrator(session_dir)
    # Force Mock Mode for testing
    c2.llm_client.mock_mode = True 
    di_results = c2.generate_di_descriptions(ranked, {"entity_name": "Test Entity"})
    print(f"   ✅ 生成了 {len(di_results)} 条 D&I 描述内容")

    # 5. Report Generation
    print("[5/5] 报告生成: 导出最终 Excel 底稿...")
    gen = ReportGenerator(session_dir)
    report_path = gen.generate(ranked, di_results, {"entity_name": "Test Entity"})
    
    if os.path.exists(report_path):
        print(f"🎉 测试圆满成功！最终底稿已生成于: {report_path}")
        # Clean up
        # shutil.rmtree(session_dir)
        return True
    else:
        print("❌ 报告生成失败：未发现底稿文件。")
        return False

if __name__ == "__main__":
    success = run_e2e_test()
    if not success:
        sys.exit(1)
