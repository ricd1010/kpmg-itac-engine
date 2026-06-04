import os
from core1_main import Core1Orchestrator
from core2_main import Core2Orchestrator
from report_generator import ReportGenerator

def run_full_pipeline():
    data_dir = r"C:\Users\Laptop\.gemini\tmp\system32\AuditHackathon\data"
    
    print(">>> 正在启动 ITAC 自动化底稿生成引擎...")
    
    # 1. Core 1: Scenario Identification & Ranking
    print(">>> [步骤 1/3] 正在识别已配置场景并计算重要性排序...")
    c1 = Core1Orchestrator(data_dir)
    ranked_scenarios = c1.run()
    print(f"    成功识别并排序了 {len(ranked_scenarios)} 个场景。")

    # 2. Core 2: AI D&I Generation
    print(">>> [步骤 2/3] 正在加载样本并调用 AI 生成 D&I 穿行测试描述...")
    c2 = Core2Orchestrator(data_dir)
    di_results = c2.generate_di_descriptions(ranked_scenarios)
    print(f"    成功为 {len(di_results)} 个匹配样本生成了 AI 描述。")

    # 3. Core 3: Report Assembly
    print(">>> [步骤 3/3] 正在拼装最终审计报告文档...")
    generator = ReportGenerator(data_dir)
    final_report_path = generator.generate(ranked_scenarios, di_results)
    
    print(f"\n✅ ITAC 自动化底稿生成完成！")
    print(f"📄 最终底稿保存路径: {final_report_path}")
    print("-" * 50)
    print("您可以打开该文件查看完整报告，它包含了场景排序、AI 生成的穿行测试文字和样本明细。")

if __name__ == "__main__":
    run_full_pipeline()
