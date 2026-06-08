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
        return s.lstrip('0') if s != '0' else '0'

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

        # 3. 汇总已识别场景 (独立输出已配置场景清单)
        results = []
        for name, acc_set in scenario_accounts.items():
            if not acc_set: continue
            
            acc_list = sorted(list(acc_set))
            # 格式化描述用于前端展示
            display_accounts = [f"{acc} ({acc_descs.get(acc, '未知科目')})" for acc in acc_list]
            
            results.append({
                "name": name,
                "accounts": display_accounts, # 前端期待格式化的列表
                "raw_accounts": acc_list,     # 后续金额匹配用原始编码
                "total_value": 0.0
            })

        # 4. 如果提供科目余额表，汇总发生额并排序
        if os.path.exists(self.tb_path) and results:
            try:
                df_tb = pd.read_csv(self.tb_path, dtype=str)
                df_tb.columns = [str(c).strip().upper() for c in df_tb.columns]
                
                tb_amounts = {}
                # 寻找金额列
                d_col = next((c for c in df_tb.columns if 'DEBIT' in c or '借方' in c), None)
                c_col = next((c for c in df_tb.columns if 'CREDIT' in c or '贷方' in c), None)
                s_col = next((c for c in df_tb.columns if 'SAKNR' in c or '科目' in c), None)

                if s_col:
                    for _, row in df_tb.iterrows():
                        saknr = self._clean_acc(row[s_col])
                        if not saknr: continue
                        
                        def parse_amt(v):
                            if pd.isna(v): return 0.0
                            return abs(float(str(v).replace(',', '')))
                        
                        val = 0.0
                        if d_col: val += parse_amt(row[d_col])
                        if c_col: val += parse_amt(row[c_col])
                        tb_amounts[saknr] = tb_amounts.get(saknr, 0) + val
                
                # 更新场景重要性
                for res in results:
                    res['total_value'] = sum(tb_amounts.get(acc, 0) for acc in res['raw_accounts'])
                
                # 依金额倒序排列
                results.sort(key=lambda x: x['total_value'], reverse=True)
            except Exception as e:
                print(f"Core 1 - Trial Balance 汇总失败: {e}")
                
        return results

if __name__ == "__main__":
    pass
