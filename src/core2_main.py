import os
import csv
import pandas as pd
from prompt_builder import PromptBuilder
from llm_client import LLMClient

class Core2Orchestrator:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.prompt_builder = PromptBuilder()
        self.llm_client = LLMClient(api_key="sk-itac-internal-use") 
        
        self.raw_samples = pd.DataFrame()
        samples_path = os.path.join(data_dir, "Samples.csv")
        if os.path.exists(samples_path):
            try:
                self.raw_samples = pd.read_csv(samples_path, dtype=str)
            except: pass

    def _clean_acc(self, val):
        """标准化科目编码"""
        s = str(val).strip().split('.')[0]
        return s.lstrip('0') if s != '0' else '0'

    def generate_di_descriptions(self, identified_scenarios, audit_context=None):
        results = []
        if audit_context is None: audit_context = {}
        if self.raw_samples.empty: return []

        # 确保列名大写
        self.raw_samples.columns = [str(c).strip().upper() for c in self.raw_samples.columns]

        # 转换金额
        if 'AMOUNT' in self.raw_samples.columns:
            def parse_amt(v):
                try: return abs(float(str(v).replace(',', '')))
                except: return 0.0
            self.raw_samples['AMT_VAL'] = self.raw_samples['AMOUNT'].apply(parse_amt)

        # 1. 对 Samples 中的科目进行清洗
        if 'SAKNR' in self.raw_samples.columns:
            self.raw_samples['SAKNR_CLEAN'] = self.raw_samples['SAKNR'].apply(self._clean_acc)

        # 2. 分组
        grouped = self.raw_samples.groupby('DOC_NUM')

        for scenario in identified_scenarios:
            scenario_name = scenario['name']
            target_account_codes = set()
            for acc_str in scenario['accounts']:
                # 提取编码并清洗
                code = self._clean_acc(acc_str.split(' ')[0])
                target_account_codes.add(code)
            
            # 遍历所有凭证组
            for doc_num, group in grouped:
                doc_accounts = set(group['SAKNR_CLEAN'].tolist())
                
                # 如果该凭证包含场景中的任何科目
                if target_account_codes.intersection(doc_accounts):
                    samples = self._synthesize_all_samples(doc_num, group, target_account_codes)
                    
                    for matching_sample in samples:
                        expected_logic = f"借: {matching_sample['DEBIT_DESC']} ({matching_sample['DEBIT_ACC']}); 贷: {matching_sample['CREDIT_DESC']} ({matching_sample['CREDIT_ACC']})"
                        
                        user_prompt = self.prompt_builder.build_prompt(
                            scenario_name=scenario_name,
                            expected_logic=expected_logic,
                            sample_row=matching_sample,
                            context=audit_context
                        )
                        
                        di_text = self.llm_client.generate_text(
                            system_prompt=self.prompt_builder.system_persona,
                            user_prompt=user_prompt
                        )
                        
                        results.append({
                            "scenario": scenario_name,
                            "sample_doc": matching_sample['DOC_NUM'],
                            "di_description": di_text,
                            "sample_table": matching_sample
                        })
        
        return results

    def _synthesize_all_samples(self, doc_num, group, target_account_codes):
        synthesized = []
        try:
            # 区分借贷
            debit_rows = group[group['SHKZG'].str.upper().isin(['S', '借'])] if 'SHKZG' in group.columns else group[group['AMT_VAL'] > 0]
            credit_rows = group[group['SHKZG'].str.upper().isin(['H', '贷'])] if 'SHKZG' in group.columns else group[group['AMT_VAL'] < 0]
            
            # 配对逻辑：金额相等且至少一方在目标科目中
            for _, d_row in debit_rows.iterrows():
                amt = abs(float(d_row['AMT_VAL']))
                d_acc_clean = self._clean_acc(d_row['SAKNR'])
                
                # 找金额匹配的贷方
                c_match = credit_rows[credit_rows['AMT_VAL'].abs() == amt]
                
                if not c_match.empty:
                    c_row = c_match.iloc[0]
                    c_acc_clean = self._clean_acc(c_row['SAKNR'])
                    
                    if d_acc_clean in target_account_codes or c_acc_clean in target_account_codes:
                        synthesized.append({
                            "DOC_NUM": doc_num,
                            "DATE": d_row.get('DATE', '2026-06-01'),
                            "DEBIT_ACC": d_row['SAKNR'],
                            "DEBIT_DESC": d_row.get('TXT50', '未定义科目'),
                            "CREDIT_ACC": c_row['SAKNR'],
                            "CREDIT_DESC": c_row.get('TXT50', '未定义科目'),
                            "AMOUNT": amt
                        })
        except: pass
        return synthesized
