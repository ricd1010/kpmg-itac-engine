from openai import OpenAI

class LLMClient:
    def __init__(self, api_key=None, model_name="deepseek-chat"):
        self.api_key = api_key
        self.model_name = model_name
        self.mock_mode = api_key is None
        if not self.mock_mode:
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )

    def validate_api_key(self):
        """
        验证 API Key 是否有效
        """
        if self.mock_mode:
            return True, "模拟模式已启用"
        try:
            # 发送一个极其微小的请求来测试 Key
            self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1
            )
            return True, "API Key 校验通过"
        except Exception as e:
            return False, f"API Key 校验失败: {str(e)}"

    def generate_text(self, system_prompt, user_prompt):
        # Attribution Footers
        ds_footer = f"\n\n[注：以上内容由 DeepSeek AI ({self.model_name}) 辅助生成，请审计人员结合实际IPE进行复核]"
        mock_footer = "\n\n[注：以上内容由 审计AI模拟引擎 生成，仅用于演示及功能验证]"

        # Base Mock Data for Fallback
        mock_response = "（AI 模拟生成）系统已根据预设配置自动生成了样本凭证，借贷方向与金额均符合审计预期逻辑。"
        if "销售发货" in user_prompt:
            mock_response = "在审计期间内，系统根据 T030 表中 GBB-VAX 的自动过账配置，在销售发货环节自动生成了凭证号为 1000001 的会计日记账。该凭证金额为 50,000.00，借记主营业务成本 (640101)，贷记库存商品 (140501)。经审计核对，该样本的财务记录与系统预设的自动结转成本逻辑完全一致，控制设计有效并得到执行。"
        elif "采购收货" in user_prompt:
            mock_response = "在审计期间内，系统根据 OBYC 中 WRX (GR/IR) 的自动过账配置，在采购收货环节自动生成了凭证号为 5000001 的会计凭证。该凭证记录金额 30,000.00，借记原材料 (140301)，贷记应付暂估 (220202)。经核对，该自动化过账行为符合 system 配置要求，穿行测试结果满意。"

        if self.mock_mode:
            return mock_response + mock_footer
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                stream=False
            )
            return response.choices[0].message.content + ds_footer
        except Exception as e:
            error_msg = str(e)
            return f"DeepSeek AI ({self.model_name}) 生成失败: {error_msg}\n\n[自动回退至模拟数据]:\n{mock_response}{mock_footer}"
