import csv

class MaterialityRanker:
    def __init__(self, tb_path):
        self.tb_path = tb_path
        self.account_amounts = {} # {saknr: total_amount}

    def load_amounts(self):
        with open(self.tb_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                saknr = row['SAKNR']
                # Sum Debit and Credit to represent "activity" for materiality ranking
                amount = abs(float(row.get('DMBTR_DEBIT', 0))) + abs(float(row.get('DMBTR_CREDIT', 0)))
                self.account_amounts[saknr] = amount
        return self.account_amounts

    def rank_scenarios(self, scenarios):
        # scenarios: list of dicts {name, accounts: [saknr1, saknr2]}
        ranked = []
        for scenario in scenarios:
            total_val = sum(self.account_amounts.get(saknr, 0) for saknr in scenario['accounts'])
            ranked.append({
                "name": scenario['name'],
                "total_value": total_val,
                "accounts": scenario['accounts']
            })
        
        # Sort by total_value descending
        ranked.sort(key=lambda x: x['total_value'], reverse=True)
        return ranked
