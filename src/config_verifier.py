import pandas as pd
import os

class ConfigVerifier:
    def __init__(self, t030_path):
        self.t030_path = t030_path
        self.configured_accounts = set()

    def _clean_acc(self, val):
        """标准化科目编码"""
        s = str(val).strip().split('.')[0]
        return s.lstrip('0') if s != '0' else '0'

    def load_configs(self):
        if not os.path.exists(self.t030_path):
            return set()
        
        try:
            df = pd.read_csv(self.t030_path, dtype=str)
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            for _, row in df.iterrows():
                k1 = row.get('KONTS')
                k2 = row.get('KONTH')
                if not pd.isna(k1): self.configured_accounts.add(self._clean_acc(k1))
                if not pd.isna(k2): self.configured_accounts.add(self._clean_acc(k2))
        except:
            pass
        return self.configured_accounts

    def verify(self, account_roles):
        """验证科目是否在 T030 中有配置"""
        verified_roles = {}
        for saknr_raw, roles in account_roles.items():
            clean_id = self._clean_acc(saknr_raw)
            if clean_id in self.configured_accounts:
                verified_roles[saknr_raw] = roles
        return verified_roles
