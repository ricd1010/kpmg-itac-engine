import os
import pandas as pd
from prompt_builder import PromptBuilder
from llm_client import LLMClient

class Core2Orchestrator:
    COUNTERPARTY_PLACEHOLDER = "OCR未识别对方科目"
    AUTO_SCENARIO_LABELS = {"", "auto", "自动识别", "自動識別", "automatic"}

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

    @staticmethod
    def _clean_acc(val):
        """标准化科目编码"""
        if pd.isna(val):
            return ""
        s = str(val).strip().split('.')[0]
        if not s or s.lower() in {"nan", "none", "null"}:
            return ""
        return s.lstrip('0') if s != '0' else '0'

    @staticmethod
    def _clean_text(val):
        if pd.isna(val):
            return ""
        text = str(val).strip()
        return "" if text.lower() in {"nan", "none", "null"} else text

    @classmethod
    def _normalize_scenario(cls, val):
        text = cls._clean_text(val)
        return "" if text.lower() in cls.AUTO_SCENARIO_LABELS or text in cls.AUTO_SCENARIO_LABELS else text

    @classmethod
    def _parse_signed_amount(cls, val):
        text = cls._clean_text(val)
        if not text:
            return 0.0
        cleaned = (
            text.replace("￥", "")
            .replace("¥", "")
            .replace("CNY", "")
            .replace("RMB", "")
            .replace(" ", "")
            .strip()
        )
        negative = (
            cleaned.startswith("-") or
            cleaned.endswith("-") or
            (cleaned.startswith("(") and cleaned.endswith(")"))
        )
        cleaned = cleaned.strip("()-")
        comma_pos = cleaned.rfind(",")
        dot_pos = cleaned.rfind(".")
        if comma_pos != -1 and dot_pos != -1:
            if comma_pos > dot_pos:
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif comma_pos != -1:
            decimal_digits = len(cleaned) - comma_pos - 1
            if decimal_digits == 2:
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif cleaned.count(".") > 1:
            parts = cleaned.split(".")
            if len(parts[-1]) == 2:
                cleaned = "".join(parts[:-1]) + "." + parts[-1]
            else:
                cleaned = "".join(parts)
        try:
            amount = float(cleaned)
        except ValueError:
            return 0.0
        return -abs(amount) if negative else amount

    @classmethod
    def _normalize_direction(cls, val, signed_amount=0.0):
        text = cls._clean_text(val).upper()
        if text in {"S", "DR", "DR.", "DEBIT", "借", "借方"}:
            return "S"
        if text in {"H", "CR", "CR.", "CREDIT", "贷", "贷方"}:
            return "H"
        return "H" if signed_amount < 0 else "S"

    @classmethod
    def normalize_sample_record(cls, record):
        signed_amount = cls._parse_signed_amount(record.get("AMOUNT"))
        amount_text = cls._clean_text(record.get("AMOUNT"))
        doc_num = cls._clean_text(record.get("DOC_NUM"))
        saknr = cls._clean_text(record.get("SAKNR"))
        txt50 = cls._clean_text(record.get("TXT50")) or "未定义科目"
        date = cls._clean_text(record.get("DATE")) or "2026-06-01"
        scenario = cls._normalize_scenario(record.get("SCENARIO"))
        return {
            "DOC_NUM": doc_num,
            "SAKNR": saknr,
            "TXT50": txt50,
            "AMOUNT": amount_text if amount_text else signed_amount,
            "SHKZG": cls._normalize_direction(record.get("SHKZG"), signed_amount),
            "DATE": date,
            "SCENARIO": scenario,
        }

    @classmethod
    def normalize_samples_dataframe(cls, df):
        if df is None or df.empty:
            return pd.DataFrame(columns=["DOC_NUM", "SAKNR", "TXT50", "AMOUNT", "SHKZG", "DATE", "SCENARIO", "AMT_SIGNED", "AMT_VAL", "SAKNR_CLEAN"])

        normalized = df.copy()
        normalized.columns = [str(c).strip().upper() for c in normalized.columns]
        for col in ["DOC_NUM", "SAKNR", "TXT50", "AMOUNT", "SHKZG", "DATE", "SCENARIO"]:
            if col not in normalized.columns:
                normalized[col] = ""

        rows = [cls.normalize_sample_record(row.to_dict()) for _, row in normalized.iterrows()]
        normalized = pd.DataFrame(rows)
        normalized["AMT_SIGNED"] = normalized["AMOUNT"].apply(cls._parse_signed_amount)
        normalized["AMT_VAL"] = normalized["AMT_SIGNED"].abs()
        normalized["SAKNR_CLEAN"] = normalized["SAKNR"].apply(cls._clean_acc)
        normalized = normalized[
            (normalized["DOC_NUM"].astype(str).str.strip() != "") &
            (normalized["SAKNR_CLEAN"].astype(str).str.strip() != "")
        ].copy()
        return normalized

    def generate_di_descriptions(self, identified_scenarios, audit_context=None):
        results = []
        if audit_context is None: audit_context = {}
        if self.raw_samples.empty: return []

        samples_df = self.normalize_samples_dataframe(self.raw_samples)
        if samples_df.empty:
            return []

        grouped = samples_df.groupby('DOC_NUM')

        for scenario in identified_scenarios:
            scenario_name = scenario['name']
            target_account_codes = set()
            for acc_str in scenario['accounts']:
                # 提取编码并清洗
                code = self._clean_acc(acc_str.split(' ')[0])
                target_account_codes.add(code)
            
            # 遍历所有凭证组
            for doc_num, group in grouped:
                specified_scenarios = {
                    self._normalize_scenario(value)
                    for value in group.get("SCENARIO", pd.Series(dtype=str)).tolist()
                    if self._normalize_scenario(value)
                }
                if specified_scenarios and scenario_name not in specified_scenarios:
                    continue

                doc_accounts = set(group['SAKNR_CLEAN'].tolist())
                
                # 如果该凭证包含场景中的任何科目
                if target_account_codes.intersection(doc_accounts):
                    samples = self._synthesize_all_samples(doc_num, group, target_account_codes)
                    
                    for matching_sample in samples:
                        matching_sample["SCENARIO"] = scenario_name
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
            debit_rows = group[group['SHKZG'].str.upper().isin(['S', '借'])]
            credit_rows = group[group['SHKZG'].str.upper().isin(['H', '贷'])]
            
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
            if not synthesized:
                balanced_sample = self._synthesize_balanced_document_sample(doc_num, debit_rows, credit_rows, target_account_codes)
                if balanced_sample:
                    synthesized.append(balanced_sample)
            if not synthesized:
                synthesized.extend(self._synthesize_single_line_samples(doc_num, group, target_account_codes))
        except Exception:
            synthesized.extend(self._synthesize_single_line_samples(doc_num, group, target_account_codes))
        return synthesized

    def _line_item(self, row):
        return {
            "account": row.get("SAKNR", ""),
            "description": row.get("TXT50", "未定义科目"),
            "amount": abs(float(row.get("AMT_VAL", 0) or 0)),
        }

    def _format_lines(self, lines, field):
        return "; ".join(str(line.get(field, "")) for line in lines if line.get(field))

    def _synthesize_balanced_document_sample(self, doc_num, debit_rows, credit_rows, target_account_codes):
        if debit_rows.empty or credit_rows.empty:
            return None

        debit_total = float(debit_rows["AMT_VAL"].sum())
        credit_total = float(credit_rows["AMT_VAL"].sum())
        if abs(debit_total - credit_total) > 0.01:
            return None

        debit_lines = [self._line_item(row) for _, row in debit_rows.iterrows()]
        credit_lines = [self._line_item(row) for _, row in credit_rows.iterrows()]
        matched_accounts = {
            self._clean_acc(line["account"])
            for line in debit_lines + credit_lines
            if self._clean_acc(line["account"]) in target_account_codes
        }
        if not matched_accounts:
            return None

        return {
            "DOC_NUM": doc_num,
            "DATE": debit_rows.iloc[0].get("DATE", credit_rows.iloc[0].get("DATE", "2026-06-01")),
            "DEBIT_ACC": self._format_lines(debit_lines, "account"),
            "DEBIT_DESC": self._format_lines(debit_lines, "description"),
            "CREDIT_ACC": self._format_lines(credit_lines, "account"),
            "CREDIT_DESC": self._format_lines(credit_lines, "description"),
            "AMOUNT": round(debit_total, 2),
            "DEBIT_LINES": debit_lines,
            "CREDIT_LINES": credit_lines,
            "BALANCED_MATCH": True,
            "MATCHED_ACCOUNTS": sorted(matched_accounts),
        }

    def _synthesize_single_line_samples(self, doc_num, group, target_account_codes):
        synthesized = []
        for _, row in group.iterrows():
            acc_clean = self._clean_acc(row.get("SAKNR", ""))
            if acc_clean not in target_account_codes:
                continue

            amount = abs(float(row.get("AMT_VAL", 0) or 0))
            account = row.get("SAKNR", "")
            description = row.get("TXT50", "未定义科目")
            direction = str(row.get("SHKZG", "S")).upper()
            if direction == "H":
                debit_acc = self.COUNTERPARTY_PLACEHOLDER
                debit_desc = self.COUNTERPARTY_PLACEHOLDER
                credit_acc = account
                credit_desc = description
            else:
                debit_acc = account
                debit_desc = description
                credit_acc = self.COUNTERPARTY_PLACEHOLDER
                credit_desc = self.COUNTERPARTY_PLACEHOLDER

            synthesized.append({
                "DOC_NUM": doc_num,
                "DATE": row.get("DATE", "2026-06-01"),
                "DEBIT_ACC": debit_acc,
                "DEBIT_DESC": debit_desc,
                "CREDIT_ACC": credit_acc,
                "CREDIT_DESC": credit_desc,
                "AMOUNT": amount,
                "OCR_FALLBACK": True,
                "OCR_NOTE": "OCR未识别完整借贷配对，已基于命中场景科目的单边记录生成描述。"
            })
        return synthesized
