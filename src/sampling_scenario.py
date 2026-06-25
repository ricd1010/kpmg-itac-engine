import re

import pandas as pd


def _clean_code(value):
    if pd.isna(value):
        return ""
    text = str(value).strip().split(".")[0]
    if not text or text.lower() in {"nan", "none", "null"}:
        return ""
    return text


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
    if t001k_df is None or t001k_df.empty:
        return lookup

    df = t001k_df.copy()
    df.columns = [str(col).strip().upper() for col in df.columns]
    for _, row in df.iterrows():
        company_code = _clean_code(row.get("BUKRS"))
        valuation_area = _clean_code(row.get("BWKEY"))
        valuation_group = _clean_code(row.get("BWMOD"))
        payload = {
            "valuation_area": valuation_area,
            "valuation_group": valuation_group,
        }
        if company_code:
            lookup[company_code] = payload
        if valuation_area and valuation_area not in lookup:
            lookup[valuation_area] = payload
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


def _select_mm03_records(company_code, valuation_area, mm03_records):
    candidates = []
    for record in mm03_records or []:
        plant = record.get("plant", "")
        valuation = record.get("valuation_area", "")
        if (
            _code_matches(plant, company_code)
            or _code_matches(plant, valuation_area)
            or _code_matches(valuation, company_code)
            or _code_matches(valuation, valuation_area)
        ):
            candidates.append(record)
    return candidates


def _join_mm03(records, key):
    values = []
    for record in records or []:
        value = str(record.get(key, "")).strip()
        if value and value not in values:
            values.append(value)
    return "；".join(values)


def _mm03_status(mm03_image_names=None, mm03_records=None, matched_records=None):
    if matched_records:
        return f"匹配 {len(matched_records)} 张"
    if mm03_records:
        return f"已解析 {len(mm03_records)} 张（本行未匹配）"
    if mm03_image_names:
        return f"已上传 {len(mm03_image_names)} 张"
    return "待补充"


def _mm03_fields(company_code, valuation_area, mm03_image_names=None, mm03_records=None):
    matched = _select_mm03_records(company_code, valuation_area, mm03_records)
    return {
        "MM03截图状态": _mm03_status(mm03_image_names, mm03_records, matched),
        "MM03匹配截图": _join_mm03(matched, "source_file"),
        "MM03物料号": _join_mm03(matched, "material_number"),
        "MM03物料描述": _join_mm03(matched, "material_description"),
        "MM03工厂": _join_mm03(matched, "plant"),
        "MM03工厂名称": _join_mm03(matched, "plant_name"),
        "MM03基本单位": _join_mm03(matched, "base_unit"),
        "MM03评估类": _join_mm03(matched, "valuation_class"),
        "MM03价格控制": _join_mm03(matched, "price_control"),
    }


def build_sampling_scenario_table(ranked_scenarios, t001k_df=None, mm03_image_names=None, mm03_records=None):
    rows = []
    t001k_lookup = _build_t001k_lookup(t001k_df)

    for scenario in ranked_scenarios or []:
        scenario_name = str(scenario.get("name", "")).strip()
        baseline_company = str(scenario.get("baseline_company_code") or "").strip()
        company_values = scenario.get("company_values") or []

        if company_values:
            for company_item in company_values:
                company_code = _clean_code(company_item.get("company_code"))
                t001k_info = t001k_lookup.get(company_code, {})
                valuation_area = t001k_info.get("valuation_area", "")
                mm03_fields = _mm03_fields(company_code, valuation_area, mm03_image_names, mm03_records)
                scenario_amount = float(company_item.get("total_value", 0) or 0)
                account_values = company_item.get("account_values") or []

                if not account_values:
                    rows.append({
                        "公司代码": company_code,
                        "评估范围": valuation_area,
                        "评估分组": t001k_info.get("valuation_group", ""),
                        "审计场景": scenario_name,
                        "基准公司": baseline_company,
                        "是否额外科目": "",
                        "科目编码": "",
                        "科目描述": "该公司最后期间未命中此场景科目",
                        "科目金额": 0.0,
                        "场景金额": scenario_amount,
                        "抽样建议": "如该场景为测试范围，请补充对应会计凭证或说明未命中原因",
                    } | mm03_fields)
                    continue

                for account in account_values:
                    is_extra = bool(account.get("is_extra"))
                    rows.append({
                        "公司代码": company_code,
                        "评估范围": valuation_area,
                        "评估分组": t001k_info.get("valuation_group", ""),
                        "审计场景": scenario_name,
                        "基准公司": baseline_company,
                        "是否额外科目": "是" if is_extra else "否",
                        "科目编码": _clean_code(account.get("account")),
                        "科目描述": str(account.get("description") or ""),
                        "科目金额": float(account.get("total_value", 0) or 0),
                        "场景金额": scenario_amount,
                        "抽样建议": "优先抽样：相比基准公司多出的实际命中科目" if is_extra else "按场景金额和样本覆盖情况抽样",
                    } | mm03_fields)
            continue

        accounts = scenario.get("accounts") or scenario.get("raw_accounts") or []
        if not accounts:
            rows.append({
                "公司代码": "",
                "评估范围": "",
                "评估分组": "",
                "审计场景": scenario_name,
                "基准公司": "",
                "是否额外科目": "",
                "科目编码": "",
                "科目描述": "未识别到关联科目",
                "科目金额": 0.0,
                "场景金额": float(scenario.get("total_value", 0) or 0),
                "抽样建议": "先完成 T030/SKAT 匹配，再上传余额表生成公司维度抽样范围",
                **_mm03_fields("", "", mm03_image_names, mm03_records),
            })
            continue

        for account_label in accounts:
            account_code, description = _parse_account_label(account_label)
            rows.append({
                "公司代码": "",
                "评估范围": "",
                "评估分组": "",
                "审计场景": scenario_name,
                "基准公司": "",
                "是否额外科目": "",
                "科目编码": account_code,
                "科目描述": description,
                "科目金额": 0.0,
                "场景金额": float(scenario.get("total_value", 0) or 0),
                "抽样建议": "上传余额表后可生成公司维度金额和优先级",
                **_mm03_fields("", "", mm03_image_names, mm03_records),
            })

    return pd.DataFrame(rows)
