class PromptBuilder:
    def __init__(self):
        self.system_persona = "你是一名四大国际会计师事务所的资深 IT 审计师，专门负责 SAP 系统自动化控制 (ITAC) 的 D&I 和 OE 测试。"
        self.template = """
### 任务
请根据提供的审计上下文、SAP 场景及样本数据，撰写一段格式标准、严谨的穿行测试描述（D&I）。

### 格式要求 (必须严格遵守)
描述必须分为以下两个部分，并使用指定的标题：

一、设计有效性测试 (TOD)
- 说明系统如何根据底层配置表（如 OBYC, T030）自动确定会计科目。
- 描述在该审计场景下，预设的自动结转逻辑（借贷方向及对应关系）。

二、执行有效性测试 (TOE)
- 结合具体样本要素进行描述。
- 必须包含：凭证号 {doc_num}、日期 {date}、借记 {debit_desc} ({debit_acc})、贷记 {credit_desc} ({credit_acc})、金额 {amount}。
- 描述核对过程：核对系统自动生成的会计凭证记录与预设逻辑一致。


结论：
- 统一使用：“经核对，该自动化过账行为符合系统预设的自动过账配置逻辑，测试结果满意。”

### 审计数据
- 被审计单位: {entity_name}
- 系统名称: {system_name}
- 审计场景: {scenario_name}
- 预期逻辑: {expected_logic}

### 撰写规范
- 语言应高度专业，避免口语化。
- 只输出上述三个部分的文字内容，不要任何前言或后记。
"""

    def build_prompt(self, scenario_name, expected_logic, sample_row, context):
        return self.template.format(
            entity_name=context.get('entity_name', '未指定'),
            system_name=context.get('system_name', '未指定'),
            scenario_name=scenario_name,
            expected_logic=expected_logic,
            doc_num=sample_row['DOC_NUM'],
            date=sample_row.get('DATE', '2025-01-01'),
            debit_acc=sample_row['DEBIT_ACC'],
            debit_desc=sample_row['DEBIT_DESC'],
            credit_acc=sample_row['CREDIT_ACC'],
            credit_desc=sample_row['CREDIT_DESC'],
            amount=sample_row['AMOUNT']
        )
