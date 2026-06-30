def amount_for_direction(account, direction_filter="全部"):
    debit_value = float(account.get("debit_value", account.get("total_value", 0)) or 0)
    credit_value = float(account.get("credit_value", 0) or 0)
    combined_value = float(account.get("combined_value", debit_value + credit_value) or 0)

    if direction_filter == "借方":
        return debit_value
    if direction_filter == "贷方":
        return credit_value
    return combined_value


def build_scenario_account_totals(ranked, direction_filter="全部"):
    rows = []
    for scenario in ranked or []:
        detail_lookup = {
            str(detail.get("account", "")).strip(): detail
            for detail in scenario.get("account_details", [])
            if detail.get("account")
        }
        by_account = {}
        for company in scenario.get("company_values", []):
            company_code = str(company.get("company_code", "未指定公司"))
            for account in company.get("account_values", []):
                account_code = str(account.get("account", "")).strip()
                if not account_code:
                    continue
                amount_value = amount_for_direction(account, direction_filter)
                if not amount_value:
                    continue

                detail = detail_lookup.get(account_code, {})
                entry = by_account.setdefault(account_code, {
                    "scenario": scenario.get("name", ""),
                    "account": account_code,
                    "description": detail.get("description") or account.get("description", "未知科目"),
                    "total_value": 0.0,
                    "debit_value": 0.0,
                    "credit_value": 0.0,
                    "company_codes": set(),
                    "company_amounts": {},
                })
                debit_value = amount_for_direction(account, "借方")
                credit_value = amount_for_direction(account, "贷方")
                entry["total_value"] += amount_value
                entry["debit_value"] += debit_value
                entry["credit_value"] += credit_value
                entry["company_codes"].add(company_code)
                company_amount = entry["company_amounts"].setdefault(company_code, {
                    "company_code": company_code,
                    "debit_value": 0.0,
                    "credit_value": 0.0,
                    "total_value": 0.0,
                })
                company_amount["debit_value"] += debit_value
                company_amount["credit_value"] += credit_value
                company_amount["total_value"] += amount_value
                description = str(account.get("description", "")).strip()
                if description and entry["description"] == "未知科目":
                    entry["description"] = description

        scenario_total = sum(float(entry["total_value"]) for entry in by_account.values())
        for entry in by_account.values():
            company_codes = sorted(entry["company_codes"])
            total_value = float(entry["total_value"])
            rows.append({
                "scenario": entry["scenario"],
                "account": entry["account"],
                "description": entry["description"],
                "total_value": total_value,
                "debit_value": float(entry["debit_value"]),
                "credit_value": float(entry["credit_value"]),
                "scenario_total_value": scenario_total,
                "amount_share_pct": (total_value / scenario_total * 100) if scenario_total else 0.0,
                "company_count": len(company_codes),
                "company_codes": company_codes,
                "company_amounts": sorted(
                    entry["company_amounts"].values(),
                    key=lambda item: (
                        -float(item["total_value"]),
                        str(item["company_code"])
                    )
                ),
            })

    return sorted(
        rows,
        key=lambda row: (
            str(row["scenario"]),
            -float(row["total_value"]),
            str(row["account"])
        )
    )
