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
            self.raw_samples = pd.read_csv(samples_path, dtype=str)

    def generate_di_descriptions(self, identified_scenarios, audit_context=None):
        results = []
        if audit_context is None: audit_context = {}
        if self.raw_samples.empty: return []

        # Ensure numeric for pairing
        if 'AMOUNT' in self.raw_samples.columns:
            self.raw_samples['AMT_VAL'] = pd.to_numeric(self.raw_samples['AMOUNT'], errors='coerce').fillna(0)

        # 1. Group by Document Number
        grouped = self.raw_samples.groupby('DOC_NUM')

        for scenario in identified_scenarios:
            scenario_name = scenario['name']
            target_account_codes = set()
            for acc_str in scenario['accounts']:
                code = acc_str.split(' ')[0]
                target_account_codes.add(code)
            
            # Find ALL matching samples for this scenario
            for doc_num, group in grouped:
                doc_accounts = set(group['SAKNR'].tolist())
                
                if target_account_codes.intersection(doc_accounts):
                    # For complex screenshots, a single document might have multiple relevant transaction pairs
                    # We'll synthesize samples for this document group
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
        """
        Attempts to extract all relevant debit/credit pairs from a document group.
        Specifically handles cases where multiple line items exist in one voucher.
        """
        synthesized = []
        try:
            debit_rows = group[group['SHKZG'].str.upper().isin(['S'])] if 'SHKZG' in group.columns else group[group['AMT_VAL'] > 0]
            credit_rows = group[group['SHKZG'].str.upper().isin(['H'])] if 'SHKZG' in group.columns else group[group['AMT_VAL'] < 0]
            
            # Match them up. Simplest approach: if counts match, pair them by order.
            # If not, try to match by absolute amount.
            for _, d_row in debit_rows.iterrows():
                # Find a credit row that "matches" this debit
                # Rule 1: Same absolute amount
                # Rule 2: At least one of the pair must be in the target_account_codes
                d_acc = str(d_row['SAKNR'])
                amt = abs(float(d_row['AMT_VAL']))
                
                # Look for a credit row with same absolute amount
                c_match = credit_rows[abs(pd.to_numeric(credit_rows['AMOUNT'], errors='coerce')) == amt]
                
                if not c_match.empty:
                    c_row = c_match.iloc[0]
                    c_acc = str(c_row['SAKNR'])
                    
                    # Verify if this pair is relevant to our current scenario
                    if d_acc in target_account_codes or c_acc in target_account_codes:
                        synthesized.append({
                            "DOC_NUM": doc_num,
                            "DATE": d_row.get('DATE', '2025-01-01'),
                            "DEBIT_ACC": d_acc,
                            "DEBIT_DESC": d_row.get('TXT50', '未定义科目'),
                            "CREDIT_ACC": c_acc,
                            "CREDIT_DESC": c_row.get('TXT50', '未定义科目'),
                            "AMOUNT": amt
                        })
        except:
            pass
        return synthesized
