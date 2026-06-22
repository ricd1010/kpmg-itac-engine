import os
import pandas as pd


def clean_account_code(val):
    if pd.isna(val):
        return ""
    text = str(val).strip().split(".")[0]
    if not text or text.lower() in {"nan", "none", "null"}:
        return ""
    return text.lstrip("0") if text != "0" else "0"


def clean_text(val):
    if pd.isna(val):
        return ""
    text = str(val).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def load_account_description_map(data_dir):
    descriptions = {}
    candidates = [
        ("SKAT.csv", ("SAKNR", "科目"), ("TXT50", "科目描述", "描述", "名称")),
        ("TrialBalance.csv", ("SAKNR", "科目"), ("TXT50", "科目描述", "描述", "名称")),
    ]

    for file_name, account_names, description_names in candidates:
        path = os.path.join(data_dir, file_name)
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path, dtype=str)
        except Exception:
            continue
        df.columns = [str(col).strip().upper() for col in df.columns]
        account_col = next((col for col in account_names if col.upper() in df.columns), None)
        desc_col = next((col for col in description_names if col.upper() in df.columns), None)
        if not account_col or not desc_col:
            continue
        account_col = account_col.upper()
        desc_col = desc_col.upper()
        for _, row in df.iterrows():
            account_code = clean_account_code(row.get(account_col))
            description = clean_text(row.get(desc_col))
            if account_code and description and account_code not in descriptions:
                descriptions[account_code] = description

    return descriptions


def enrich_samples_with_account_descriptions(samples, descriptions):
    enriched = []
    for sample in samples or []:
        item = dict(sample)
        account_code = clean_account_code(item.get("SAKNR"))
        if account_code in descriptions:
            item["TXT50"] = descriptions[account_code]
        enriched.append(item)
    return enriched
