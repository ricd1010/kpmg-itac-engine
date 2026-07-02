import pandas as pd

from core2_main import Core2Orchestrator
from voucher_validation import validate_voucher_t030_logic


LEDGER_BASE_COLUMNS = [
    "DOC_NUM", "COMPANY_CODE", "DATE", "SAKNR", "TXT50", "MATNR",
    "WERKS", "AMOUNT", "SHKZG", "KTOSL", "KOMOK",
]


def _clean_text(value):
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


def _normalize_direction(value, signed_amount=0.0):
    text = _clean_text(value).upper()
    if text in {"S", "DR", "DR.", "DEBIT", "借", "借方"}:
        return "S"
    if text in {"H", "CR", "CR.", "CREDIT", "贷", "贷方"}:
        return "H"
    return "H" if float(signed_amount or 0) < 0 else "S"


def _direction_label(direction):
    return "贷方" if direction == "H" else "借方"


def _split_meta(value):
    text = _clean_text(value).upper()
    if not text:
        return set()
    parts = []
    for chunk in text.replace("/", ";").replace(",", ";").replace("，", ";").replace("；", ";").split(";"):
        item = chunk.strip()
        if item:
            parts.append(item)
    return set(parts)


def normalize_ledger_dataframe(df):
    if df is None or not hasattr(df, "empty") or df.empty:
        return pd.DataFrame(columns=LEDGER_BASE_COLUMNS + ["AMT_SIGNED", "AMT_ABS", "SAKNR_CLEAN", "DIRECTION"])

    normalized = df.copy()
    normalized.columns = [str(col).strip().upper() for col in normalized.columns]
    for col in LEDGER_BASE_COLUMNS:
        if col not in normalized.columns:
            normalized[col] = ""

    rows = []
    for _, row in normalized.iterrows():
        signed_amount = Core2Orchestrator._parse_signed_amount(row.get("AMOUNT"))
        direction = _normalize_direction(row.get("SHKZG"), signed_amount)
        rows.append({
            "DOC_NUM": _clean_text(row.get("DOC_NUM")),
            "COMPANY_CODE": _clean_code(row.get("COMPANY_CODE")),
            "DATE": _clean_text(row.get("DATE")),
            "SAKNR": _clean_code(row.get("SAKNR")),
            "SAKNR_CLEAN": _clean_account(row.get("SAKNR")),
            "TXT50": _clean_text(row.get("TXT50")),
            "MATNR": _clean_code(row.get("MATNR")),
            "WERKS": _clean_code(row.get("WERKS")),
            "AMOUNT": _clean_text(row.get("AMOUNT")),
            "AMT_SIGNED": signed_amount,
            "AMT_ABS": abs(float(signed_amount or 0)),
            "SHKZG": direction,
            "DIRECTION": _direction_label(direction),
            "KTOSL": _clean_text(row.get("KTOSL")).upper(),
            "KOMOK": _clean_text(row.get("KOMOK")).upper(),
        })
    result = pd.DataFrame(rows)
    return result[
        (result["DOC_NUM"].astype(str).str.strip() != "")
        & (result["SAKNR_CLEAN"].astype(str).str.strip() != "")
    ].reset_index(drop=True)


def _build_scenario_rules(ranked):
    rules_by_account = {}
    for scenario in ranked or []:
        scenario_name = _clean_text(scenario.get("name"))
        if not scenario_name:
            continue
        details = scenario.get("account_details") or []
        seen_accounts = set()
        for detail in details:
            account = _clean_account(detail.get("account"))
            if not account:
                continue
            seen_accounts.add(account)
            rules_by_account.setdefault(account, []).append({
                "scenario": scenario_name,
                "account": account,
                "ktosl": _split_meta(detail.get("ktosl")),
                "komok": _split_meta(detail.get("komok")),
                "direction": _clean_text(detail.get("direction")),
                "specificity": len(_split_meta(detail.get("ktosl"))) + len(_split_meta(detail.get("komok"))),
            })
        for account in scenario.get("amount_accounts") or scenario.get("raw_accounts") or []:
            account = _clean_account(account)
            if not account or account in seen_accounts:
                continue
            rules_by_account.setdefault(account, []).append({
                "scenario": scenario_name,
                "account": account,
                "ktosl": set(),
                "komok": set(),
                "direction": "",
                "specificity": 0,
            })
    return rules_by_account


def _score_rule(row, rule):
    score = 1
    row_ktosl = _clean_text(row.get("KTOSL")).upper()
    row_komok = _clean_text(row.get("KOMOK")).upper()
    rule_ktosl = rule.get("ktosl") or set()
    rule_komok = rule.get("komok") or set()

    if row_ktosl and rule_ktosl:
        if row_ktosl in rule_ktosl:
            score += 6
        else:
            return 0
    elif row_ktosl and not rule_ktosl:
        score += 1

    if row_komok and rule_komok:
        if row_komok in rule_komok:
            score += 3
        else:
            return 0
    elif row_komok and not rule_komok:
        score += 1

    direction = _clean_text(rule.get("direction"))
    if direction:
        row_direction = _direction_label(row.get("SHKZG"))
        if direction == row_direction or direction == "借贷双方":
            score += 1
    score += int(rule.get("specificity") or 0)
    return score


def classify_ledger_scenarios(ledger_df, ranked):
    ledger = normalize_ledger_dataframe(ledger_df)
    if ledger.empty:
        return ledger
    rules_by_account = _build_scenario_rules(ranked)
    rows = []
    for _, row in ledger.iterrows():
        item = row.to_dict()
        account = item.get("SAKNR_CLEAN", "")
        rules = rules_by_account.get(account, [])
        scored = []
        for rule in rules:
            score = _score_rule(item, rule)
            if score:
                scored.append((score, rule))
        if not scored:
            item["SCENARIO"] = ""
            item["SCENARIO_MATCH_STATUS"] = "无法匹配自动化场景"
            item["SCENARIO_MATCH_REASON"] = "科目未落入当前自动化凭证场景库"
        else:
            best_score = max(score for score, _ in scored)
            best_rules = [rule for score, rule in scored if score == best_score]
            scenario_names = sorted({rule["scenario"] for rule in best_rules})
            item["SCENARIO"] = "；".join(scenario_names)
            if len(scenario_names) == 1:
                item["SCENARIO_MATCH_STATUS"] = "自动化场景已匹配"
                item["SCENARIO_MATCH_REASON"] = "科目及可用事务字段命中场景规则"
            else:
                item["SCENARIO_MATCH_STATUS"] = "多场景候选"
                item["SCENARIO_MATCH_REASON"] = "同一科目命中多个场景，请结合事务类型或业务文本复核"
        rows.append(item)
    return pd.DataFrame(rows)


def analyze_ledger(ledger_df, ranked, t030_df=None, t001k_df=None, mm03_records=None, marc_df=None):
    tagged = classify_ledger_scenarios(ledger_df, ranked)
    if tagged.empty:
        return tagged

    validation_input = tagged.copy()
    validation_input["SCENARIO"] = validation_input["SCENARIO"].apply(
        lambda value: str(value).split("；")[0] if str(value or "").strip() else ""
    )
    validation = validate_voucher_t030_logic(validation_input, t030_df, t001k_df, mm03_records, marc_df)
    validation = validation.reset_index(drop=True)
    tagged = tagged.reset_index(drop=True)

    conclusions = validation["校验结论"].tolist() if not validation.empty and "校验结论" in validation.columns else []
    notes = validation["校验说明"].tolist() if not validation.empty and "校验说明" in validation.columns else []
    expected = validation["T030期望科目"].tolist() if not validation.empty and "T030期望科目" in validation.columns else []

    tagged["CONFIG_VALIDATION_STATUS"] = [_standard_config_status(conclusions[idx] if idx < len(conclusions) else "待补充") for idx in range(len(tagged))]
    tagged["CONFIG_VALIDATION_NOTE"] = [notes[idx] if idx < len(notes) else "" for idx in range(len(tagged))]
    tagged["T030_EXPECTED_ACCOUNT"] = [expected[idx] if idx < len(expected) else "" for idx in range(len(tagged))]
    tagged["SUBSTANTIVE_TEST_STATUS"] = tagged.apply(
        lambda row: "已完成实质性测试"
        if row.get("SCENARIO_MATCH_STATUS") == "自动化场景已匹配" and row.get("CONFIG_VALIDATION_STATUS") == "配置逻辑通过"
        else "未完成实质性测试",
        axis=1,
    )
    tagged["EXCEPTION_TYPE"] = tagged.apply(_exception_type, axis=1)
    return tagged


def _exception_type(row):
    if row.get("SUBSTANTIVE_TEST_STATUS") == "已完成实质性测试":
        return ""
    if row.get("SCENARIO_MATCH_STATUS") == "无法匹配自动化场景":
        return "无法匹配自动化场景"
    if row.get("SCENARIO_MATCH_STATUS") == "多场景候选":
        return "多场景候选，需补充事务字段"
    status = _clean_text(row.get("CONFIG_VALIDATION_STATUS"))
    if status == "字段待补充":
        return _field_gap_reason(row.get("CONFIG_VALIDATION_NOTE"))
    if status and status != "配置逻辑通过":
        return status
    return "无法完成自动化测试"


def _standard_config_status(status):
    status = _clean_text(status)
    if status == "通过":
        return "配置逻辑通过"
    if status == "不一致":
        return "配置逻辑不通过"
    if status in {"待补充", "待核对"}:
        return "字段待补充"
    return status or "字段待补充"


def _field_gap_reason(note):
    note = _clean_text(note)
    if "公司代码" in note:
        return "缺少公司代码"
    if "物料号" in note:
        return "缺少物料号"
    if "T001K" in note:
        return "缺少 T001K"
    if "MARC" in note or "MM03" in note or "评估分类" in note:
        return "缺少 MARC/MM03"
    if "T030" in note:
        return "缺少 T030 或配置未命中"
    return "字段待补充"


def ledger_display_dataframe(analysis_df):
    if analysis_df is None or not hasattr(analysis_df, "empty") or analysis_df.empty:
        return pd.DataFrame()
    df = analysis_df.copy()
    columns = {
        "SUBSTANTIVE_TEST_STATUS": "实质性测试状态",
        "EXCEPTION_TYPE": "异常类型",
        "SCENARIO": "自动化场景",
        "SCENARIO_MATCH_STATUS": "场景匹配状态",
        "CONFIG_VALIDATION_STATUS": "配置验证结论",
        "DOC_NUM": "凭证号",
        "COMPANY_CODE": "公司代码",
        "DATE": "日期",
        "SAKNR": "科目编码",
        "TXT50": "科目描述",
        "MATNR": "物料号",
        "WERKS": "工厂",
        "DIRECTION": "借贷方向",
        "AMT_ABS": "金额",
        "KTOSL": "事务",
        "KOMOK": "科目修改",
        "T030_EXPECTED_ACCOUNT": "T030期望科目",
        "CONFIG_VALIDATION_NOTE": "验证说明",
    }
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[list(columns)].rename(columns=columns)


def build_ledger_coverage_summary(analysis_df):
    if analysis_df is None or not hasattr(analysis_df, "empty") or analysis_df.empty:
        return {
            "total_lines": 0,
            "covered_lines": 0,
            "exception_lines": 0,
            "total_amount": 0.0,
            "covered_amount": 0.0,
            "exception_amount": 0.0,
            "amount_coverage_pct": 0.0,
            "total_accounts": 0,
            "covered_accounts": 0,
            "account_coverage_pct": 0.0,
        }
    df = analysis_df.copy()
    completed = df["SUBSTANTIVE_TEST_STATUS"].eq("已完成实质性测试")
    total_amount = float(df["AMT_ABS"].sum())
    covered_amount = float(df.loc[completed, "AMT_ABS"].sum())
    total_accounts = df["SAKNR_CLEAN"].astype(str).replace("", pd.NA).dropna().nunique()
    covered_accounts = df.loc[completed, "SAKNR_CLEAN"].astype(str).replace("", pd.NA).dropna().nunique()
    return {
        "total_lines": int(len(df)),
        "covered_lines": int(completed.sum()),
        "exception_lines": int((~completed).sum()),
        "total_amount": total_amount,
        "covered_amount": covered_amount,
        "exception_amount": total_amount - covered_amount,
        "amount_coverage_pct": (covered_amount / total_amount * 100) if total_amount else 0.0,
        "total_accounts": int(total_accounts),
        "covered_accounts": int(covered_accounts),
        "account_coverage_pct": (covered_accounts / total_accounts * 100) if total_accounts else 0.0,
    }


def build_exception_ledger(analysis_df):
    display_df = ledger_display_dataframe(analysis_df)
    if display_df.empty:
        return display_df
    return display_df[display_df["实质性测试状态"] != "已完成实质性测试"].reset_index(drop=True)


def build_ledger_dashboard_tables(analysis_df):
    display_df = ledger_display_dataframe(analysis_df)
    if display_df.empty:
        return {"scenario": pd.DataFrame(), "exception": pd.DataFrame()}
    scenario = (
        display_df.groupby(["自动化场景", "实质性测试状态"], dropna=False, as_index=False)
        .agg(凭证行数=("凭证号", "count"), 金额=("金额", "sum"), 科目数=("科目编码", "nunique"))
        .sort_values("金额", ascending=False)
    )
    exception = (
        display_df[display_df["实质性测试状态"] != "已完成实质性测试"]
        .groupby(["异常类型"], dropna=False, as_index=False)
        .agg(凭证行数=("凭证号", "count"), 金额=("金额", "sum"), 科目数=("科目编码", "nunique"))
        .sort_values("金额", ascending=False)
    )
    return {"scenario": scenario, "exception": exception}
