from llm_client import LLMClient
from core2_main import Core2Orchestrator
import os

def test_deepseek_logic():
    print("=== DeepSeek 接入全套测试 (验证模式) ===")
    
    # 1. 验证 LLMClient 是否已更新为 DeepSeek
    print("\n[Step 1] 检查 LLMClient 配置...")
    client = LLMClient(api_key="sk-dummy-key-for-test")
    print(f"当前模型名称: {client.model_name}")
    if hasattr(client, 'client') and "deepseek" in str(client.client.base_url):
        print("✅ LLMClient 已指向 DeepSeek API 端点")
    else:
        print("❌ LLMClient 未正确指向 DeepSeek")

    # 2. 模拟运行核心流程，查看生成结果的来源标识
    print("\n[Step 2] 模拟核心底稿生成流程 (API 调用验证)...")
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    c2 = Core2Orchestrator(data_dir)
    
    # 注入带有 dummy key 的 client，触发 API 调用逻辑
    # 注意：这会产生报错，但报错信息中应包含 "DeepSeek AI" 的标识，从而证明逻辑已切换
    c2.llm_client = LLMClient(api_key="sk-test-verify-only")
    
    mock_scenarios = [{"name": "2.1.1 销售发货", "accounts": ["640101", "140501"]}]
    results = c2.generate_di_descriptions(mock_scenarios)
    
    for res in results:
        print(f"\n生成场景: {res['scenario']}")
        print(f"生成的 D&I 描述片段:\n{res['di_description'][:150]}...")
        
        if "DeepSeek AI" in res['di_description']:
            print("\n✅ 验证通过：底稿内容生成的逻辑已明确切换至 DeepSeek 引擎。")
        else:
            print("\n❌ 验证失败：内容中未发现 DeepSeek 标识。")

if __name__ == "__main__":
    test_deepseek_logic()
