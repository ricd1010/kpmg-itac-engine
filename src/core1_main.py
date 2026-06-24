import os
import pandas as pd

class Core1Orchestrator:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.t030_path = os.path.join(data_dir, "T030.csv")
        self.skat_path = os.path.join(data_dir, "SKAT.csv")
        self.tb_path = os.path.join(data_dir, "TrialBalance.csv")
        
        # 预置覆盖场景的自动记账规则映射 (KTOSL, KOMOK)
        # 规则说明：如果 KOMOK 为空字符串，则只匹配 KTOSL；如果定义了 KOMOK，则两者均需匹配。
        self.preset_mappings = {
            "销售发货": [("GBB", "VAX"), ("GBB", "VAY"), ("GISS", "")],
            "销售入账": [("REV", ""), ("AKTY", ""), ("MWS", "")],
            "销售成本结转": [("GBB", "VAX"), ("GBB", "VAY")],
            "收款核销": [("AKTY", "")],
            "采购收货": [("BSX", ""), ("WRX", "")],
            "采购入账": [("WRX", ""), ("AKTP", ""), ("VST", "")],
            "生产领料": [("GBB", "VBO"), ("GBB", "VBR"), ("BSX", "")],
            "完工入库": [("GBB", "AUF"), ("BSX", "")],
            "工单差异": [("PRD", ""), ("GBB", "AUF")],
            "产成品差异": [("UMSK", ""), ("PRD", "PRA")]
        }
        # 金额归集使用更特异的自动记账规则，避免 BSX 等共享库存科目在多个场景重复计入。
        self.amount_mappings = {
            "销售发货": [("GBB", "VAX"), ("GBB", "VAY"), ("GISS", "")],
            "销售入账": [("REV", ""), ("MWS", "")],
            "销售成本结转": [("GBB", "VAX"), ("GBB", "VAY")],
            "收款核销": [("AKTY", "")],
            "采购收货": [("WRX", "")],
            "采购入账": [("AKTP", ""), ("VST", "")],
            "生产领料": [("GBB", "VBO"), ("GBB", "VBR")],
            "完工入库": [("GBB", "AUF")],
            "工单差异": [("PRD", "")],
            "产成品差异": [("UMSK", ""), ("PRD", "PRA")]
        }
        self.amount_account_include_prefixes = {
            # GBB-AUF 中可能混入物料消耗等费用科目，完工入库金额只取完工转出科目。
            "完工入库": ("500108", "500109"),
        }
        self.amount_rule_exclusions = {
            # PRD-PRA 已单独作为产成品差异，避免同时进入工单差异。
            "工单差异": [("PRD", "PRA")],
        }
        self.amount_account_exclusion_sources = {
            # 同一差异科目可能同时配置多个 PRD 修改码；产成品差异优先于工单差异。
            "工单差异": ("产成品差异",),
        }

    def _clean_acc(self, val):
        if pd.isna(val): return None
        s = str(val).strip().split('.')[0]
        if not s or s.lower() in {"nan", "none", "null"}:
            return None
        return s.lstrip('0') if s != '0' else '0'

    def _parse_amt(self, val):
        if pd.isna(val): return 0.0
        cleaned = str(val).replace(',', '').strip()
        if not cleaned or cleaned.lower() in {"nan", "none", "null"}:
            return 0.0
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _company_label(self, val):
        if pd.isna(val): return "未指定公司"
        s = str(val).strip().split('.')[0]
        if not s or s.lower() in {"nan", "none", "null"}:
            return "未指定公司"
        return s

    def _clean_meta(self, val):
        if pd.isna(val):
            return ""
        s = str(val).strip()
        if not s or s.lower() in {"nan", "none", "null"}:
            return ""
        return s.split(".")[0] if s.endswith(".0") else s

    def _rule_matches(self, ktosl, komok, rule_ktosl, rule_komok):
        if ktosl != rule_ktosl:
            return False
        return not rule_komok or komok == rule_komok

    def _amount_rule_excluded(self, scenario_name, ktosl, komok):
        return any(
            self._rule_matches(ktosl, komok, rule_ktosl, rule_komok)
            for rule_ktosl, rule_komok in self.amount_rule_exclusions.get(scenario_name, [])
        )

    def _account_allowed_for_amount(self, scenario_name, account_code):
        prefixes = self.amount_account_include_prefixes.get(scenario_name)
        if not prefixes:
            return True
        return any(str(account_code).startswith(prefix) for prefix in prefixes)

    def _add_amount_account(self, scenario_amount_accounts, scenario_name, account_code):
        if account_code and self._account_allowed_for_amount(scenario_name, account_code):
            scenario_amount_accounts[scenario_name].add(account_code)

    def _apply_amount_account_precedence(self, scenario_amount_accounts):
        for scenario_name, source_names in self.amount_account_exclusion_sources.items():
            target_accounts = scenario_amount_accounts.get(scenario_name)
            if target_accounts is None:
                continue
            for source_name in source_names:
                target_accounts.difference_update(scenario_amount_accounts.get(source_name, set()))

    def _merge_account_detail(self, detail_map, account_code, direction, ktosl, komok, bwmod, bklas):
        if not account_code:
            return
        detail = detail_map.setdefault(account_code, {
            "directions": set(),
            "ktosl": set(),
            "komok": set(),
            "bwmod": set(),
            "bklas": set(),
        })
        detail["directions"].add(direction)
        for key, value in (
            ("ktosl", ktosl),
            ("komok", komok),
            ("bwmod", bwmod),
            ("bklas", bklas),
        ):
            if value:
                detail[key].add(value)

    def _format_direction(self, directions):
        direction_set = set(directions or [])
        if {"借方", "贷方"}.issubset(direction_set):
            return "借贷双方"
        if "借方" in direction_set:
            return "借方"
        if "贷方" in direction_set:
            return "贷方"
        return ""

    def _format_meta_set(self, values):
        return " / ".join(sorted(str(value) for value in values if value))

    def _build_account_details(self, detail_map, acc_descs):
        details = []
        for account_code in sorted(detail_map):
            detail = detail_map[account_code]
            details.append({
                "account": account_code,
                "description": acc_descs.get(account_code, "未知科目"),
                "direction": self._format_direction(detail.get("directions")),
                "ktosl": self._format_meta_set(detail.get("ktosl")),
                "komok": self._format_meta_set(detail.get("komok")),
                "bwmod": self._format_meta_set(detail.get("bwmod")),
                "bklas": self._format_meta_set(detail.get("bklas")),
            })
        return details

    def _apply_baseline_flags(self, company_values):
        candidates = [item for item in company_values if item.get("account_values")]
        if not candidates:
            return None, [], 0

        baseline = min(
            candidates,
            key=lambda item: (
                len(item.get("account_values", [])),
                float(item.get("total_value", 0) or 0),
                str(item.get("company_code", ""))
            )
        )
        baseline_company_code = str(baseline.get("company_code", ""))
        baseline_accounts = {
            str(account.get("account", ""))
            for account in baseline.get("account_values", [])
            if account.get("account")
        }
        extra_accounts = set()

        for item in company_values:
            for account in item.get("account_values", []):
                account_code = str(account.get("account", ""))
                is_extra = bool(account_code and account_code not in baseline_accounts)
                account["is_extra"] = is_extra
                account["baseline_company_code"] = baseline_company_code
                if is_extra:
                    extra_accounts.add(account_code)

        return baseline_company_code, sorted(baseline_accounts), len(extra_accounts)

    def run(self):
        # 1. 解析 T030，提取已配置的科目
        # 结果结构：{ scenario_name: set(account_codes) }
        scenario_accounts = {name: set() for name in self.preset_mappings.keys()}
        scenario_amount_accounts = {name: set() for name in self.preset_mappings.keys()}
        scenario_account_details = {name: {} for name in self.preset_mappings.keys()}
        
        if os.path.exists(self.t030_path):
            try:
                df_t030 = pd.read_csv(self.t030_path, dtype=str)
                df_t030.columns = [str(c).strip().upper() for c in df_t030.columns]
                
                for _, row in df_t030.iterrows():
                    ktosl = self._clean_meta(row.get('KTOSL')).upper()
                    komok = self._clean_meta(row.get('KOMOK')).upper()
                    bwmod = self._clean_meta(row.get('BWMOD'))
                    bklas = self._clean_meta(row.get('BKLAS'))
                    k1 = self._clean_acc(row.get('KONTS'))
                    k2 = self._clean_acc(row.get('KONTH'))
                    
                    if not ktosl: continue
                    
                    for sc_name, rules in self.preset_mappings.items():
                        for r_ktosl, r_komok in rules:
                            if self._rule_matches(ktosl, komok, r_ktosl, r_komok):
                                if k1: scenario_accounts[sc_name].add(k1)
                                if k2: scenario_accounts[sc_name].add(k2)
                                self._merge_account_detail(scenario_account_details[sc_name], k1, "借方", ktosl, komok, bwmod, bklas)
                                self._merge_account_detail(scenario_account_details[sc_name], k2, "贷方", ktosl, komok, bwmod, bklas)
                    for sc_name, rules in self.amount_mappings.items():
                        if self._amount_rule_excluded(sc_name, ktosl, komok):
                            continue
                        for r_ktosl, r_komok in rules:
                            if self._rule_matches(ktosl, komok, r_ktosl, r_komok):
                                self._add_amount_account(scenario_amount_accounts, sc_name, k1)
                                self._add_amount_account(scenario_amount_accounts, sc_name, k2)
            except Exception as e:
                print(f"Core 1 - T030 解析失败: {e}")
        self._apply_amount_account_precedence(scenario_amount_accounts)

        # 2. 读取 SKAT 获取描述 (辅助展示)
        acc_descs = {}
        if os.path.exists(self.skat_path):
            try:
                df_skat = pd.read_csv(self.skat_path, dtype=str)
                df_skat.columns = [str(c).strip().upper() for c in df_skat.columns]
                s_col = 'SAKNR' if 'SAKNR' in df_skat.columns else '科目'
                t_col = 'TXT50' if 'TXT50' in df_skat.columns else '科目描述'
                
                if s_col in df_skat.columns and t_col in df_skat.columns:
                    for _, row in df_skat.iterrows():
                        k = self._clean_acc(row[s_col])
                        if k: acc_descs[k] = str(row[t_col]).strip()
            except: pass

        # 3. 如果提供科目余额表，按公司代码取各自最后期间，汇总本月借方发生额；同时用余额表 TXT50 补足 SKAT 缺失描述
        tb_amounts = {}
        tb_debit_amounts = {}
        tb_credit_amounts = {}
        tb_combined_amounts = {}
        tb_amounts_by_company = {}
        has_directional_amounts = False
        if os.path.exists(self.tb_path):
            try:
                df_tb = pd.read_csv(self.tb_path, dtype=str)
                df_tb.columns = [str(c).strip().upper() for c in df_tb.columns]
                
                d_col = 'DMBTR_DEBIT' if 'DMBTR_DEBIT' in df_tb.columns else next((c for c in df_tb.columns if 'DEBIT' in c or '借方' in c), None)
                c_col = 'DMBTR_CREDIT' if 'DMBTR_CREDIT' in df_tb.columns else next((c for c in df_tb.columns if 'CREDIT' in c or '贷方' in c), None)
                has_directional_amounts = bool(c_col)
                s_col = 'SAKNR' if 'SAKNR' in df_tb.columns else next((c for c in df_tb.columns if '科目' in c), None)
                t_col = 'TXT50' if 'TXT50' in df_tb.columns else next((c for c in df_tb.columns if '描述' in c or '名称' in c), None)
                company_col = next((c for c in df_tb.columns if c == 'COMPANY_CODE' or '公司代码' in c or 'BUKRS' in c), None)
                period_col = next((c for c in df_tb.columns if c == 'PERIOD' or '会计期间' in c or '会计期' in c or 'MONAT' in c), None)

                if s_col and t_col:
                    for _, row in df_tb.iterrows():
                        saknr = self._clean_acc(row[s_col])
                        if not saknr or saknr in acc_descs:
                            continue
                        desc = str(row[t_col]).strip()
                        if desc and desc.lower() != "nan":
                            acc_descs[saknr] = desc

                df_scope = df_tb
                if period_col:
                    df_scope = df_tb.copy()
                    df_scope["_PERIOD_SORT"] = pd.to_numeric(
                        df_scope[period_col].astype(str).str.replace(r'\.0$', '', regex=True),
                        errors="coerce"
                    )
                    if df_scope["_PERIOD_SORT"].notna().any():
                        if company_col:
                            max_period = df_scope.groupby(company_col)["_PERIOD_SORT"].transform("max")
                            df_scope = df_scope[df_scope["_PERIOD_SORT"].eq(max_period)]
                        else:
                            df_scope = df_scope[df_scope["_PERIOD_SORT"].eq(df_scope["_PERIOD_SORT"].max())]

                if s_col:
                    for _, row in df_scope.iterrows():
                        saknr = self._clean_acc(row[s_col])
                        if not saknr: continue
                        
                        debit_val = self._parse_amt(row[d_col]) if d_col else 0.0
                        credit_val = abs(self._parse_amt(row[c_col])) if c_col else 0.0
                        combined_val = debit_val + credit_val

                        tb_debit_amounts[saknr] = tb_debit_amounts.get(saknr, 0) + debit_val
                        tb_credit_amounts[saknr] = tb_credit_amounts.get(saknr, 0) + credit_val
                        tb_combined_amounts[saknr] = tb_combined_amounts.get(saknr, 0) + combined_val
                        tb_amounts[saknr] = tb_debit_amounts[saknr]
                        company_code = self._company_label(row[company_col]) if company_col else "未指定公司"
                        company_amounts = tb_amounts_by_company.setdefault(company_code, {})
                        account_amounts = company_amounts.setdefault(saknr, {
                            "debit_value": 0.0,
                            "credit_value": 0.0,
                            "combined_value": 0.0,
                        })
                        account_amounts["debit_value"] += debit_val
                        account_amounts["credit_value"] += credit_val
                        account_amounts["combined_value"] += combined_val
            except Exception as e:
                print(f"Core 1 - Trial Balance 汇总失败: {e}")

        # 4. 保留全部预设场景；未命中的场景显示为空科目、金额为 0
        results = []
        for name, acc_set in scenario_accounts.items():
            acc_list = sorted(list(acc_set))
            amount_acc_list = sorted(list(scenario_amount_accounts.get(name, set())))
            display_accounts = [f"{acc} ({acc_descs.get(acc, '未知科目')})" for acc in acc_list]
            account_details = self._build_account_details(scenario_account_details.get(name, {}), acc_descs)
            company_values = []
            for company_code, amount_map in tb_amounts_by_company.items():
                company_debit_total = sum(float(amount_map.get(acc, {}).get("debit_value", 0) or 0) for acc in amount_acc_list)
                company_credit_total = sum(float(amount_map.get(acc, {}).get("credit_value", 0) or 0) for acc in amount_acc_list)
                company_combined_total = company_debit_total + company_credit_total
                if company_combined_total:
                    account_values = []
                    for acc in amount_acc_list:
                        account_amounts = amount_map.get(acc, {})
                        account_debit_total = float(account_amounts.get("debit_value", 0) or 0)
                        account_credit_total = float(account_amounts.get("credit_value", 0) or 0)
                        account_combined_total = account_debit_total + account_credit_total
                        if account_combined_total:
                            account_entry = {
                                "account": acc,
                                "description": acc_descs.get(acc, "未知科目"),
                                "total_value": account_debit_total,
                            }
                            if has_directional_amounts:
                                account_entry.update({
                                    "debit_value": account_debit_total,
                                    "credit_value": account_credit_total,
                                    "combined_value": account_combined_total,
                                })
                            account_values.append(account_entry)
                    company_entry = {
                        "company_code": company_code,
                        "total_value": company_debit_total,
                        "account_values": account_values
                    }
                    if has_directional_amounts:
                        company_entry.update({
                            "debit_value": company_debit_total,
                            "credit_value": company_credit_total,
                            "combined_value": company_combined_total,
                        })
                    company_values.append(company_entry)
            company_values.sort(key=lambda x: x["total_value"], reverse=True)
            baseline_company_code, baseline_account_codes, extra_account_count = self._apply_baseline_flags(company_values)

            results.append({
                "name": name,
                "accounts": display_accounts,
                "account_details": account_details,
                "raw_accounts": acc_list,
                "amount_accounts": amount_acc_list,
                "total_value": sum(tb_amounts.get(acc, 0) for acc in amount_acc_list),
                "debit_value": sum(tb_debit_amounts.get(acc, 0) for acc in amount_acc_list),
                "credit_value": sum(tb_credit_amounts.get(acc, 0) for acc in amount_acc_list),
                "combined_value": sum(tb_combined_amounts.get(acc, 0) for acc in amount_acc_list),
                "company_values": company_values,
                "baseline_company_code": baseline_company_code,
                "baseline_account_codes": baseline_account_codes,
                "extra_account_count": extra_account_count
            })

        results.sort(key=lambda x: x['total_value'], reverse=True)
        return results

if __name__ == "__main__":
    pass
