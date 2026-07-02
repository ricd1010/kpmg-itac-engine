import re

import pandas as pd
from mm03_parser import normalize_plant_code


def _clean_code(value):
    if isinstance(value, (list, tuple, set)):
        value = next((item for item in value if str(item).strip()), "")
    elif isinstance(value, dict):
        value = next((item for item in value.values() if str(item).strip()), "")
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        return ""
    text = str(value).strip().split(".")[0]
    if not text or text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def _as_float(value):
    if isinstance(value, (list, tuple, set, dict)):
        return 0.0
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _as_dict(value):
    return value if isinstance(value, dict) else {}


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _account_amount(account):
    account = _as_dict(account)
    return _as_float(account.get("combined_value", account.get("total_value")))


def _scenario_account_share_map(scenario):
    by_account = {}
    for company_item in _as_list(scenario.get("company_values")):
        company_item = _as_dict(company_item)
        for account in _as_list(company_item.get("account_values")):
            account = _as_dict(account)
            account_code = _clean_code(account.get("account"))
            if not account_code:
                continue
            by_account[account_code] = by_account.get(account_code, 0.0) + _account_amount(account)

    scenario_total = sum(value for value in by_account.values() if value)
    if not scenario_total:
        return {}
    return {
        account_code: value / scenario_total * 100
        for account_code, value in by_account.items()
    }


def _format_pct(value):
    return f"{float(value):.2f}%" if value else ""


def _parse_account_label(label):
    text = str(label or "").strip()
    if not text:
        return "", ""
    match = re.match(r"^(\d+)\s*\((.*)\)$", text)
    if match:
        return _clean_code(match.group(1)), match.group(2).strip()
    parts = text.split(maxsplit=1)
    account = _clean_code(parts[0])
    description = parts[1].strip("() ") if len(parts) > 1 else ""
    return account, description


def _build_t001k_lookup(t001k_df):
    lookup = {}
    if t001k_df is None or not hasattr(t001k_df, "empty") or t001k_df.empty:
        return lookup

    df = t001k_df.copy()
    df.columns = [str(col).strip().upper() for col in df.columns]
    for _, row in df.iterrows():
        company_code = _clean_code(row.get("BUKRS"))
        valuation_group = _clean_code(row.get("BWMOD"))
        payload = {
            "valuation_group": valuation_group,
        }
        if company_code:
            lookup[company_code] = payload
    return lookup


def _code_matches(left, right):
    left = _clean_code(left)
    right = _clean_code(right)
    if not left or not right:
        return False
    if left == right:
        return True
    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    if len(longer) - len(shorter) != 1:
        return False
    return any(longer[:idx] + longer[idx + 1:] == shorter for idx in range(len(longer)))


def _select_mm03_records(company_code, valuation_group, mm03_records):
    candidates = []
    for record in _as_list(mm03_records):
        if not isinstance(record, dict):
            continue
        plant = record.get("plant", "")
        if (
            _code_matches(plant, company_code)
            or _code_matches(plant, valuation_group)
        ):
            candidates.append(record)
    return candidates


def _join_mm03(records, key):
    values = []
    for record in _as_list(records):
        if not isinstance(record, dict):
            continue
        raw_value = record.get(key, "")
        if key in {"material_number", "plant", "valuation_class"}:
            value = normalize_plant_code(raw_value) if key == "plant" else _clean_code(raw_value)
        else:
            if isinstance(raw_value, (list, tuple, set)):
                raw_value = next((item for item in raw_value if str(item).strip()), "")
            elif isinstance(raw_value, dict):
                raw_value = next((item for item in raw_value.values() if str(item).strip()), "")
            value = str(raw_value).strip()
        if value and value not in values:
            values.append(value)
    return "；".join(values)


def _mm03_status(mm03_image_names=None, mm03_records=None, matched_records=None):
    if matched_records:
        return f"匹配 {len(matched_records)} 张"
    record_count = len(_as_list(mm03_records))
    image_count = len(_as_list(mm03_image_names))
    if record_count:
        return f"已解析 {record_count} 张（本行未匹配）"
    if image_count:
        return f"已上传 {image_count} 张"
    return "待补充"


def _mm03_fields(company_code, valuation_group, mm03_image_names=None, mm03_records=None):
    matched = _select_mm03_records(company_code, valuation_group, mm03_records)
    return {
        "MM03截图状态": _mm03_status(mm03_image_names, mm03_records, matched),
        "MM03物料号": _join_mm03(matched, "material_number"),
        "MM03工厂编号": _join_mm03(matched, "plant"),
        "MM03评估分类": _join_mm03(matched, "valuation_class"),
    }


def build_sampling_scenario_table(ranked_scenarios, t001k_df=None, mm03_image_names=None, mm03_records=None):
    rows = []
    t001k_lookup = _build_t001k_lookup(t001k_df)

    for scenario in _as_list(ranked_scenarios):
        scenario = _as_dict(scenario)
        scenario_name = str(scenario.get("name", "")).strip()
        company_values = _as_list(scenario.get("company_values"))
        account_share_map = _scenario_account_share_map(scenario)

        if company_values:
            for company_item in company_values:
                company_item = _as_dict(company_item)
                company_code = _clean_code(company_item.get("company_code"))
                t001k_info = t001k_lookup.get(company_code, {})
                valuation_group = t001k_info.get("valuation_group", "")
                mm03_fields = _mm03_fields(company_code, valuation_group, mm03_image_names, mm03_records)
                scenario_amount = _as_float(company_item.get("total_value"))
                account_values = _as_list(company_item.get("account_values"))

                if not account_values:
                    rows.append({
                        "公司代码": company_code,
                        "T001K评估分组代码": valuation_group,
                        "审计场景": scenario_name,
                        "科目编码": "",
                        "科目描述": "该公司最后期间未命中此场景科目",
                        "科目金额": 0.0,
                        "占比": "",
                        "场景金额": scenario_amount,
                        "抽样建议": "如该场景为审计覆盖范围，请补充对应会计凭证或说明未命中原因",
                    } | mm03_fields)
                    continue

                for account in account_values:
                    account = _as_dict(account)
                    account_code = _clean_code(account.get("account"))
                    rows.append({
                        "公司代码": company_code,
                        "T001K评估分组代码": valuation_group,
                        "审计场景": scenario_name,
                        "科目编码": account_code,
                        "科目描述": str(account.get("description") or ""),
                        "科目金额": _as_float(account.get("total_value")),
                        "占比": _format_pct(account_share_map.get(account_code, 0.0)),
                        "场景金额": scenario_amount,
                        "抽样建议": "按场景金额、科目占比和样本覆盖情况抽样",
                    } | mm03_fields)
            continue

        accounts = _as_list(scenario.get("accounts") or scenario.get("raw_accounts"))
        if not accounts:
            rows.append({
                "公司代码": "",
                "T001K评估分组代码": "",
                "审计场景": scenario_name,
                "科目编码": "",
                "科目描述": "未识别到关联科目",
                "科目金额": 0.0,
                "占比": "",
                "场景金额": _as_float(scenario.get("total_value")),
                "抽样建议": "先完成 T030/SKAT 匹配，再上传余额表生成公司维度抽样范围",
                **_mm03_fields("", "", mm03_image_names, mm03_records),
            })
            continue

        for account_label in accounts:
            account_code, description = _parse_account_label(account_label)
            rows.append({
                "公司代码": "",
                "T001K评估分组代码": "",
                "审计场景": scenario_name,
                "科目编码": account_code,
                "科目描述": description,
                "科目金额": 0.0,
                "占比": "",
                "场景金额": _as_float(scenario.get("total_value")),
                "抽样建议": "上传余额表后可生成公司维度金额和优先级",
                **_mm03_fields("", "", mm03_image_names, mm03_records),
            })

    return pd.DataFrame(rows)
