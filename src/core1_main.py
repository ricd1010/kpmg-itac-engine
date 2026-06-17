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
            return abs(float(cleaned))
        except ValueError:
            return 0.0

    def _company_label(self, val):
        if pd.isna(val): return "未指定公司"
        s = str(val).strip().split('.')[0]
        if not s or s.lower() in {"nan", "none", "null"}:
            return "未指定公司"
        return s

    def run(self):
        # 1. 解析 T030，提取已配置的科目
        # 结果结构：{ scenario_name: set(account_codes) }
        scenario_accounts = {name: set() for name in self.preset_mappings.keys()}
        
        if os.path.exists(self.t030_path):
            try:
                df_t030 = pd.read_csv(self.t030_path, dtype=str)
                df_t030.columns = [str(c).strip().upper() for c in df_t030.columns]
                
                for _, row in df_t030.iterrows():
                    ktosl = str(row.get('KTOSL', '')).strip().upper()
                    komok = str(row.get('KOMOK', '')).strip().upper()
                    k1 = self._clean_acc(row.get('KONTS'))
                    k2 = self._clean_acc(row.get('KONTH'))
                    
                    if not ktosl: continue
                    
                    for sc_name, rules in self.preset_mappings.items():
                        for r_ktosl, r_komok in rules:
                            if ktosl == r_ktosl:
                                # 匹配逻辑：规则没定义 KOMOK 或 显式定义且相等
                                if not r_komok or (komok == r_komok):
                                    if k1: scenario_accounts[sc_name].add(k1)
                                    if k2: scenario_accounts[sc_name].add(k2)
            except Exception as e:
                print(f"Core 1 - T030 解析失败: {e}")

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

        # 3. 如果提供科目余额表，按公司代码取各自最后期间，汇总本年累计发生额；同时用余额表 TXT50 补足 SKAT 缺失描述
        tb_amounts = {}
        tb_amounts_by_company = {}
        if os.path.exists(self.tb_path):
            try:
                df_tb = pd.read_csv(self.tb_path, dtype=str)
                df_tb.columns = [str(c).strip().upper() for c in df_tb.columns]
                
                d_col = 'DMBTR_DEBIT' if 'DMBTR_DEBIT' in df_tb.columns else next((c for c in df_tb.columns if 'DEBIT' in c or '借方' in c), None)
                c_col = 'DMBTR_CREDIT' if 'DMBTR_CREDIT' in df_tb.columns else next((c for c in df_tb.columns if 'CREDIT' in c or '贷方' in c), None)
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
                        
                        val = 0.0
                        if d_col: val += self._parse_amt(row[d_col])
                        if c_col: val += self._parse_amt(row[c_col])
                        tb_amounts[saknr] = tb_amounts.get(saknr, 0) + val
                        company_code = self._company_label(row[company_col]) if company_col else "未指定公司"
                        tb_amounts_by_company.setdefault(company_code, {})
                        tb_amounts_by_company[company_code][saknr] = tb_amounts_by_company[company_code].get(saknr, 0) + val
            except Exception as e:
                print(f"Core 1 - Trial Balance 汇总失败: {e}")

        # 4. 保留全部预设场景；未命中的场景显示为空科目、金额为 0
        results = []
        for name, acc_set in scenario_accounts.items():
            acc_list = sorted(list(acc_set))
            display_accounts = [f"{acc} ({acc_descs.get(acc, '未知科目')})" for acc in acc_list]
            company_values = []
            for company_code, amount_map in tb_amounts_by_company.items():
                company_total = sum(amount_map.get(acc, 0) for acc in acc_list)
                if company_total:
                    company_values.append({
                        "company_code": company_code,
                        "total_value": company_total
                    })
            company_values.sort(key=lambda x: x["total_value"], reverse=True)

            results.append({
                "name": name,
                "accounts": display_accounts,
                "raw_accounts": acc_list,
                "total_value": sum(tb_amounts.get(acc, 0) for acc in acc_list),
                "company_values": company_values
            })

        results.sort(key=lambda x: x['total_value'], reverse=True)
        return results

if __name__ == "__main__":
    pass
