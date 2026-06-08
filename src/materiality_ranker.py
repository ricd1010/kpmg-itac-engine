import pandas as pd
import os

class MaterialityRanker:
    def __init__(self, tb_path):
        self.tb_path = tb_path
        self.account_amounts = {} 

    def _clean_acc(self, val):
        """标准化科目编码：去空格，去 .0，去前导零"""
        s = str(val).strip().split('.')[0]
        return s.lstrip('0') if s != '0' else '0'

    def load_amounts(self):
        """使用 Pandas 健壮加载"""
        if not os.path.exists(self.tb_path):
            return {}
            
        try:
            # 强制按字符串读取，防止 SAKNR 变成浮点数
            df = pd.read_csv(self.tb_path, dtype=str)
            # 标准化所有列名为大写并去空格
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            for _, row in df.iterrows():
                saknr_raw = row.get('SAKNR')
                if pd.isna(saknr_raw): continue
                
                saknr = self._clean_acc(saknr_raw)
                
                # 转换金额，处理可能的逗号
                def parse_amt(v):
                    if pd.isna(v): return 0.0
                    return abs(float(str(v).replace(',', '')))
                
                d = parse_amt(row.get('DMBTR_DEBIT', 0))
                c = parse_amt(row.get('DMBTR_CREDIT', 0))
                
                # 累加活跃度
                self.account_amounts[saknr] = self.account_amounts.get(saknr, 0) + (d + c)
        except Exception as e:
            print(f"MaterialityRanker Error: {e}")
        return self.account_amounts

    def rank_scenarios(self, scenarios):
        ranked = []
        for scenario in scenarios:
            # 同样对场景内的科目进行标准化匹配
            total_val = 0
            for acc in scenario['accounts']:
                clean_id = self._clean_acc(acc)
                total_val += self.account_amounts.get(clean_id, 0)
                
            ranked.append({
                "name": scenario['name'],
                "total_value": total_val,
                "accounts": scenario['accounts']
            })
        
        ranked.sort(key=lambda x: x['total_value'], reverse=True)
        return ranked
