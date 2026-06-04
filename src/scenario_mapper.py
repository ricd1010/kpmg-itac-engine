import csv
import re
import os

class AccountMapper:
    def __init__(self, skat_path):
        self.skat_path = skat_path
        self.account_roles = {} # {saknr: [role1, role2]}
        self.account_descs = {} # {saknr: desc}
        self.role_keywords = {
            "REVENUE": ["主营业务收入", "营业收入", "销售收入", "其他业务收入"],
            "COGS": ["主营业务成本", "营业成本", "销售成本", "其他业务成本"],
            "RAW_MATERIAL": ["原材料", "原辅料", "辅料", "包装物"],
            "FIN_GOODS": ["库存商品", "产成品", "半成品", "委托加工物资"],
            "AR": ["应收账款", "应收票据"],
            "AP": ["应付账款", "应付票据"],
            "GRIR": ["应付暂估", "GR/IR", "材料采购"],
            "VAT_OUT": ["应交税费", "销项"],
            "VAT_IN": ["应交税费", "进项"],
            "PROD_COST": ["生产成本", "制造费用"],
            "PPV": ["材料成本差异"],
            "VAR_FG": ["产成品差异", "商品差异"],
            "VAR_FG_TRANS": ["结转产成品差异"],
            "GOODS_ISSUE": ["发出商品"]
        }

    def load_and_classify(self):
        # 1. First, load from SKAT (Primary source)
        raw_dict = {}
        if os.path.exists(self.skat_path):
            with open(self.skat_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    raw_dict[row['SAKNR']] = row['TXT50']
        
        # 2. Augmented with TrialBalance (Secondary source, fills the gaps)
        tb_path = self.skat_path.replace("SKAT.csv", "TrialBalance.csv")
        if os.path.exists(tb_path):
            with open(tb_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['SAKNR'] not in raw_dict or len(raw_dict[row['SAKNR']]) < 3:
                        raw_dict[row['SAKNR']] = row.get('TXT50', '')

        # 3. Classify based on the combined dictionary
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

if __name__ == "__main__":
    mapper = AccountMapper(r"C:\Users\Laptop\.gemini\tmp\system32\AuditHackathon\data\SKAT.csv")
    roles = mapper.load_and_classify()
    print(f"Classified {len(roles)} accounts.")
    for saknr, roles_list in roles.items():
        print(f"Account {saknr}: {roles_list}")
