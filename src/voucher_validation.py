import pandas as pd

from mm03_parser import normalize_plant_code


def _clean_text(value):
    if isinstance(value, (list, tuple, set)):
        value = next((item for item in value if str(item).strip()), "")
    elif isinstance(value, dict):
        value = next((item for item in value.values() if str(item).strip()), "")
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def _clean_code(value):
    text = _clean_text(value)
    if not text:
        return ""
    return text.split(".")[0]


def _clean_account(value):
    code = _clean_code(value)
    if not code:
        return ""
    return code.lstrip("0") if code != "0" else "0"


def _normalize_direction(value, amount=None):
    text = _clean_text(value).upper()
    if text in {"S", "DR", "DEBIT", "借", "借方"}:
        return "S"
    if text in {"H", "CR", "CREDIT", "贷", "贷方"}:
        return "H"
    try:
        return "H" if float(amount or 0) < 0 else "S"
    except (TypeError, ValueError):
        return "S"


def _direction_account_column(direction):
    return "KONTH" if direction == "H" else "KONTS"


def _direction_label(direction):
    return "贷方" if direction == "H" else "借方"


def _first_matching_column(df, candidates):
    upper = {str(col).strip().upper(): col for col in df.columns}
    for candidate in candidates:
        found = upper.get(candidate.upper())
        if found is not None:
            return found
    return None


def build_t001k_lookup(t001k_df):
    lookup = {}
    if t001k_df is None or not hasattr(t001k_df, "empty") or t001k_df.empty:
        return lookup
    df = t001k_df.copy()
    df.columns = [str(col).strip().upper() for col in df.columns]
    company_col = _first_matching_column(df, ["BUKRS", "COMPANY_CODE"])
    group_col = _first_matching_column(df, ["BWMOD"])
    if not company_col or not group_col:
        return lookup
    for _, row in df.iterrows():
        company_code = _clean_code(row.get(company_col))
        valuation_group = _clean_code(row.get(group_col))
        if company_code:
            lookup[company_code] = valuation_group
    return lookup


def build_mm03_lookup(mm03_records):
    lookup = {}
    for record in mm03_records or []:
        if not isinstance(record, dict):
            continue
        material = _clean_code(record.get("material_number") or record.get("MATNR"))
        if not material:
            continue
        lookup.setdefault(material, []).append({
            "material_number": material,
            "plant": normalize_plant_code(record.get("plant", "")),
            "valuation_class": _clean_code(record.get("valuation_class") or record.get("BKLAS")),
            "source_file": _clean_text(record.get("source_file")),
        })
    return lookup


def _code_related(left, right):
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


def _pick_mm03_record(records, company_code, valuation_group):
    if not records:
        return {}
    for record in records:
        plant = record.get("plant", "")
        if _code_related(plant, company_code) or _code_related(plant, valuation_group):
            return record
    return records[0]


def _prepare_t030(t030_df):
    if t030_df is None or not hasattr(t030_df, "empty") or t030_df.empty:
        return pd.DataFrame()
    df = t030_df.copy()
    df.columns = [str(col).strip().upper() for col in df.columns]
    for col in ["KTOSL", "KOMOK", "BWMOD", "BKLAS", "KONTS", "KONTH"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].apply(_clean_code if col in {"BWMOD", "BKLAS", "KONTS", "KONTH"} else _clean_text)
        if col in {"KTOSL", "KOMOK"}:
            df[col] = df[col].astype(str).str.upper()
    return df


def _filter_t030(t030_df, valuation_group, valuation_class, ktosl="", komok=""):
    if t030_df.empty:
        return t030_df
    mask = pd.Series(True, index=t030_df.index)
    if valuation_group:
        mask &= t030_df["BWMOD"].isin(["", valuation_group])
    if valuation_class:
        mask &= t030_df["BKLAS"].isin(["", valuation_class])
    ktosl = _clean_text(ktosl).upper()
    komok = _clean_text(komok).upper()
    if ktosl:
        mask &= t030_df["KTOSL"].eq(ktosl)
    if komok:
        mask &= t030_df["KOMOK"].isin(["", komok])
    return t030_df[mask].copy()


def validate_voucher_t030_logic(samples_df, t030_df, t001k_df=None, mm03_records=None):
    if samples_df is None or not hasattr(samples_df, "empty") or samples_df.empty:
        return pd.DataFrame()

    samples = samples_df.copy()
    samples.columns = [str(col).strip().upper() for col in samples.columns]
    for col in ["DOC_NUM", "SCENARIO", "COMPANY_CODE", "MATNR", "SAKNR", "SHKZG", "AMOUNT", "KTOSL", "KOMOK"]:
        if col not in samples.columns:
            samples[col] = ""

    t030 = _prepare_t030(t030_df)
    t001k_lookup = build_t001k_lookup(t001k_df)
    mm03_lookup = build_mm03_lookup(mm03_records)
    rows = []

    for _, sample in samples.iterrows():
        doc_num = _clean_text(sample.get("DOC_NUM"))
        scenario = _clean_text(sample.get("SCENARIO"))
        company_code = _clean_code(sample.get("COMPANY_CODE"))
        material = _clean_code(sample.get("MATNR"))
        account = _clean_account(sample.get("SAKNR"))
        direction = _normalize_direction(sample.get("SHKZG"), sample.get("AMOUNT"))
        valuation_group = t001k_lookup.get(company_code, "")
        mm03_record = _pick_mm03_record(mm03_lookup.get(material, []), company_code, valuation_group)
        valuation_class = _clean_code(mm03_record.get("valuation_class"))
        expected_col = _direction_account_column(direction)
        expected_accounts = []
        status = "通过"
        note = ""

        if not company_code:
            status = "待补充"
            note = "缺少凭证公司代码，无法定位 T001K 评估分组。"
        elif not valuation_group:
            status = "待补充"
            note = "T001K 未找到该公司代码对应评估分组。"
        elif not material:
            status = "待补充"
            note = "缺少凭证物料号，无法定位 MM03 评估分类。"
        elif not valuation_class:
            status = "待补充"
            note = "MM03 未找到该物料号对应评估分类。"
        elif t030.empty:
            status = "待补充"
            note = "缺少 T030 配置表，无法校验自动过账逻辑。"
        else:
            matched_config = _filter_t030(
                t030,
                valuation_group,
                valuation_class,
                sample.get("KTOSL"),
                sample.get("KOMOK"),
            )
            expected_accounts = sorted({
                _clean_account(value)
                for value in matched_config.get(expected_col, pd.Series(dtype=str)).tolist()
                if _clean_account(value)
            })
            if not expected_accounts:
                status = "待核对"
                note = "未找到与评估分组、评估分类及凭证事务匹配的 T030 科目配置。"
            elif account not in expected_accounts:
                status = "不一致"
                note = "凭证科目未落在 T030 对应借贷方向配置科目中。"
            else:
                note = "凭证科目、公司评估分组、物料评估分类与 T030 配置一致。"

        rows.append({
            "凭证号": doc_num,
            "审计场景": scenario,
            "公司代码": company_code,
            "物料号": material,
            "科目编码": account,
            "借贷方向": _direction_label(direction),
            "T001K评估分组": valuation_group,
            "MM03工厂": mm03_record.get("plant", ""),
            "MM03评估分类": valuation_class,
            "T030期望科目": "；".join(expected_accounts),
            "校验结论": status,
            "校验说明": note,
        })

    return pd.DataFrame(rows)
