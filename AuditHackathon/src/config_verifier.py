import csv

class ConfigVerifier:
    def __init__(self, t030_path):
        self.t030_path = t030_path
        self.configured_accounts = set()

    def load_configs(self):
        with open(self.t030_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # SAP T030 stores accounts in KONTS (Debit) or KONTH (Credit)
                if row['KONTS']:
                    self.configured_accounts.add(row['KONTS'])
                if row['KONTH']:
                    self.configured_accounts.add(row['KONTH'])
        return self.configured_accounts

    def verify(self, account_roles):
        verified_roles = {}
        for saknr, roles in account_roles.items():
            if saknr in self.configured_accounts:
                verified_roles[saknr] = roles
        return verified_roles

if __name__ == "__main__":
    verifier = ConfigVerifier(r"C:\Users\Laptop\.gemini\tmp\system32\AuditHackathon\data\T030.csv")
    configs = verifier.load_configs()
    print(f"Loaded {len(configs)} configured accounts from T030.")
