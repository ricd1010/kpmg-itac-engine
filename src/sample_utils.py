import os
import pandas as pd

SAMPLE_PREVIEW_COLUMNS = [
    "SOURCE_TYPE",
    "SOURCE_FILE",
    "SCENARIO",
    "DOC_NUM",
    "COMPANY_CODE",
    "DATE",
    "SAKNR",
    "TXT50",
    "MATNR",
    "AMOUNT",
    "SHKZG",
    "KTOSL",
    "KOMOK",
]


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


def _editor_text_value(value):
    if pd.isna(value):
        return ""
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return ""
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def prepare_sample_editor_dataframe(records, scenario_options, preferred_columns=None):
    """Build a Streamlit data_editor-safe sample preview dataframe.

    st.data_editor checks each configured column against the underlying pandas
    dtype. Sample uploads often parse AMOUNT as numeric and DATE as datetime,
    while the UI intentionally uses text columns so users can correct OCR/export
    values. Normalize the preview dataframe to object/string cells before
    rendering to avoid column type compatibility errors.
    """
    columns = list(preferred_columns or SAMPLE_PREVIEW_COLUMNS)
    df = pd.DataFrame(records or [])
    for col in columns:
        if col not in df.columns:
            df[col] = ""

    allowed_scenarios = set(scenario_options or [])
    df["SCENARIO"] = df["SCENARIO"].map(_editor_text_value).apply(
        lambda value: value if value in allowed_scenarios else ""
    )

    for col in df.columns:
        if col != "SCENARIO":
            df[col] = df[col].map(_editor_text_value)

    remaining_columns = [col for col in df.columns if col not in columns]
    return df[columns + remaining_columns]
