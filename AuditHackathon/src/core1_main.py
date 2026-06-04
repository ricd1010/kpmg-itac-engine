import os
from scenario_mapper import AccountMapper
from config_verifier import ConfigVerifier
from materiality_ranker import MaterialityRanker

class Core1Orchestrator:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.mapper = AccountMapper(os.path.join(data_dir, "SKAT.csv"))
        self.verifier = ConfigVerifier(os.path.join(data_dir, "T030.csv"))
        self.ranker = MaterialityRanker(os.path.join(data_dir, "TrialBalance.csv"))

    def run(self):
        # 1. Map account descriptions to roles
        account_roles = self.mapper.load_and_classify()
        
        # 2. Verify against T030
        self.verifier.load_configs()
        verified_roles = self.verifier.verify(account_roles)
        
        # 3. All 10 standard ITAC scenarios
        scenario_definitions = [
            {"id": "2.1.1", "name": "销售发货", "roles": ["FIN_GOODS", "COGS"]},
            {"id": "2.1.2", "name": "销售入账", "roles": ["AR", "REVENUE", "VAT_OUT"]},
            {"id": "2.1.3", "name": "销售成本结转", "roles": ["COGS", "FIN_GOODS"]},
            {"id": "2.1.4", "name": "收款核销", "roles": ["AR"]},
            {"id": "2.2.1", "name": "采购收货", "roles": ["RAW_MATERIAL", "GRIR"]},
            {"id": "2.2.2", "name": "采购入账", "roles": ["GRIR", "AP", "VAT_IN"]},
            {"id": "2.3.1", "name": "生产领料", "roles": ["PROD_COST", "RAW_MATERIAL"]},
            {"id": "2.3.2", "name": "完工入库", "roles": ["FIN_GOODS", "PROD_COST"]},
            {"id": "2.3.3", "name": "工单差异", "roles": ["PROD_COST", "VAR_FG"]},
            {"id": "2.3.4", "name": "产成品差异", "roles": ["FIN_GOODS", "VAR_FG_TRANS"]}
        ]

        scenarios_found = []
        for defn in scenario_definitions:
            matching_saknrs = []
            formatted_descs = []
            for saknr, roles in verified_roles.items():
                if any(r in roles for r in defn['roles']):
                    matching_saknrs.append(saknr)
                    desc = self.mapper.account_descs.get(saknr, "未知科目")
                    formatted_descs.append(f"{saknr} ({desc})")
            
            scenarios_found.append({
                "name": f"{defn['name']}",
                "accounts": matching_saknrs, # Raw IDs for ranker
                "display_accounts": formatted_descs # Pre-save formatted list
            })
        
        # 4. Rank by materiality
        self.ranker.load_amounts()
        # materiality_ranker returns a NEW list of dicts
        ranked = self.ranker.rank_scenarios(scenarios_found)
        
        # We need to map back 'display_accounts' because the ranker creates new dicts
        display_map = {s['name']: s['display_accounts'] for s in scenarios_found}
        
        for r in ranked:
            r['accounts'] = display_map.get(r['name'], [])
            
        return ranked

if __name__ == "__main__":
    pass
