import pandas as pd
import re
import os

class AccountMapper:
    def __init__(self, skat_path):
        self.skat_path = skat_path
        self.account_roles = {} 
        self.account_descs = {} 
        self.role_keywords = {
            "REVENUE": ["主营业务收入", "营业收入", "销售收入", "其他业务收入", "主营收入", "销售额"],
            "COGS": ["主营业务成本", "营业成本", "销售成本", "其他业务成本", "销售支出"],
            "RAW_MATERIAL": ["原材料", "原辅料", "辅料", "包装物", "材料", "包材"],
            "FIN_GOODS": ["库存商品", "产成品", "半成品", "委托加工物资", "商品", "产成品", "半成"],
            "AR": ["应收账款", "应收票据", "应收"],
            "AP": ["应付账款", "应付票据", "应付"],
            "GRIR": ["应付暂估", "GR/IR", "材料采购", "暂估", "采购收货"],
            "VAT_OUT": ["应交税费", "销项", "进项税额", "增值税"],
            "VAT_IN": ["应交税费", "进项", "增值税"],
            "PROD_COST": ["生产成本", "制造费用", "研发支出"],
            "PPV": ["材料成本差异"],
            "VAR_FG": ["产成品差异", "商品差异"],
            "VAR_FG_TRANS": ["结转产成品差异"],
            "GOODS_ISSUE": ["发出商品"]
        }

    def _clean_acc(self, val):
        s = str(val).strip().split('.')[0]
        return s.lstrip('0') if s != '0' else '0'

    def load_and_classify(self):
        raw_dict = {}
        
        # 统一读取逻辑：扫描所有可能的列，寻找 SAKNR 和 TXT50
        def smart_extract(df):
            sak_col = None
            txt_col = None
            # 优先找完全匹配
            for c in df.columns:
                c_str = str(c).upper()
                if "SAKNR" == c_str: sak_col = c
                if "TXT50" == c_str: txt_col = c
            
            # 模糊找
            if not sak_col:
                for c in df.columns:
                    c_str = str(c)
                    if "总帐科目" in c_str or "总账科目" in c_str or "科目" in c_str:
                        sak_col = c; break
            if not txt_col:
                for c in df.columns:
                    c_str = str(c)
                    if "短文本" in c_str or "描述" in c_str or "名称" in c_str:
                        txt_col = c; break
            
            if sak_col and txt_col:
                for _, row in df.iterrows():
                    s_val = self._clean_acc(row[sak_col])
                    t_val = str(row[txt_col]).strip()
                    if s_val and s_val != 'nan':
                        raw_dict[s_val] = t_val

        # 1. 加载 SKAT
        if os.path.exists(self.skat_path):
            try:
                df = pd.read_csv(self.skat_path, dtype=str)
                smart_extract(df)
            except: pass
        
        # 2. 加载 余额表 补全
        tb_path = self.skat_path.replace("SKAT.csv", "TrialBalance.csv")
        if os.path.exists(tb_path):
            try:
                df = pd.read_csv(tb_path, dtype=str)
                smart_extract(df)
            except: pass

        # 3. 分类
        for saknr, txt50 in raw_dict.items():
            self.account_descs[saknr] = txt50
            roles = []
            for role, keywords in self.role_keywords.items():
                if any(kw in txt50 for kw in keywords):
                    if role == "VAT_OUT" and "销项" not in txt50: continue
                    if role == "VAT_IN" and "进项" not in txt50: continue
                    roles.append(role)
            if roles:
                self.account_roles[saknr] = roles
        
        return self.account_roles
