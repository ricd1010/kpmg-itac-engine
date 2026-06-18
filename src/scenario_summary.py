def build_scenario_account_totals(ranked):
    rows = []
    for scenario in ranked or []:
        by_account = {}
        for company in scenario.get("company_values", []):
            company_code = str(company.get("company_code", "未指定公司"))
            for account in company.get("account_values", []):
                account_code = str(account.get("account", "")).strip()
                if not account_code:
                    continue
                entry = by_account.setdefault(account_code, {
                    "scenario": scenario.get("name", ""),
                    "account": account_code,
                    "description": account.get("description", "未知科目"),
                    "total_value": 0.0,
                    "company_codes": set(),
                    "extra_company_count": 0,
                })
                entry["total_value"] += float(account.get("total_value", 0) or 0)
                entry["company_codes"].add(company_code)
                if account.get("is_extra"):
                    entry["extra_company_count"] += 1
                description = str(account.get("description", "")).strip()
                if description and entry["description"] == "未知科目":
                    entry["description"] = description

        for entry in by_account.values():
            company_codes = sorted(entry["company_codes"])
            rows.append({
                "scenario": entry["scenario"],
                "account": entry["account"],
                "description": entry["description"],
                "total_value": entry["total_value"],
                "company_count": len(company_codes),
                "company_codes": company_codes,
                "extra_company_count": entry["extra_company_count"],
            })

    return sorted(
        rows,
        key=lambda row: (
            str(row["scenario"]),
            -float(row["total_value"]),
            str(row["account"])
        )
    )
