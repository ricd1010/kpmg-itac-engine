import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sample_utils import (
    build_sample_voucher_index,
    enrich_samples_with_account_descriptions,
    is_duplicate_voucher_sample,
    load_account_description_map,
    prepare_sample_editor_dataframe,
    remove_duplicate_ocr_samples,
)


def test_load_account_description_map_prefers_skat(tmp_path):
    (tmp_path / "SKAT.csv").write_text(
        "SAKNR,TXT50\n2202040000,应付账款-GR/IR\n1405020000,库存商品-自制成品\n",
        encoding="utf-8-sig",
    )
    (tmp_path / "TrialBalance.csv").write_text(
        "SAKNR,TXT50\n2202040000,应付账款-GR/余额表\n",
        encoding="utf-8-sig",
    )

    descriptions = load_account_description_map(tmp_path)

    assert descriptions["2202040000"] == "应付账款-GR/IR"
    assert descriptions["1405020000"] == "库存商品-自制成品"


def test_enrich_samples_with_account_descriptions_replaces_bad_ocr_text():
    samples = [{
        "DOC_NUM": "6000004976",
        "SAKNR": "2202040000",
        "TXT50": "应付账款-GR/珢",
        "AMOUNT": "598.470,60-",
    }]

    enriched = enrich_samples_with_account_descriptions(samples, {
        "2202040000": "应付账款-GR/IR"
    })

    assert enriched[0]["TXT50"] == "应付账款-GR/IR"
    assert samples[0]["TXT50"] == "应付账款-GR/珢"


def test_prepare_sample_editor_dataframe_stringifies_editable_values():
    prepared = prepare_sample_editor_dataframe(
        [
            {
                "SOURCE_TYPE": "table",
                "SOURCE_FILE": "fb03.xlsx",
                "SCENARIO": "Purchase",
                "DOC_NUM": "6000004976",
                "DATE": pd.Timestamp("2026-06-25"),
                "SAKNR": "1405020000",
                "TXT50": "inventory",
                "MATNR": 10000000,
                "AMOUNT": 528470.34,
                "SHKZG": "S",
            },
            {
                "SCENARIO": "Unknown",
                "AMOUNT": None,
            },
        ],
        ["Purchase"],
    )

    assert prepared.loc[0, "AMOUNT"] == "528470.34"
    assert prepared.loc[0, "DATE"] == "2026-06-25"
    assert prepared.loc[0, "MATNR"] == "10000000"
    assert prepared.loc[1, "SCENARIO"] == ""
    assert all(dtype == "object" for dtype in prepared.dtypes.astype(str))


def test_voucher_index_treats_same_excel_and_ocr_voucher_as_duplicate():
    table_records = [
        {"DOC_NUM": "6000004976", "COMPANY_CODE": "4020", "SAKNR": "1405020000"},
        {"DOC_NUM": "6000004976", "COMPANY_CODE": "4020", "SAKNR": "2202040000"},
    ]
    voucher_index = build_sample_voucher_index(table_records)

    assert is_duplicate_voucher_sample(
        {"DOC_NUM": "6000004976", "COMPANY_CODE": "4020", "SAKNR": "1405050100"},
        voucher_index,
    )
    assert not is_duplicate_voucher_sample(
        {"DOC_NUM": "6000004976", "COMPANY_CODE": "4300", "SAKNR": "1405050100"},
        voucher_index,
    )


def test_voucher_duplicate_check_falls_back_to_document_when_company_missing():
    voucher_index = build_sample_voucher_index([
        {"DOC_NUM": 8178095898.0, "COMPANY_CODE": "", "SAKNR": "6401000000"}
    ])

    assert is_duplicate_voucher_sample(
        {"DOC_NUM": "8178095898", "COMPANY_CODE": "4110", "SAKNR": "1405010000"},
        voucher_index,
    )


def test_remove_duplicate_ocr_samples_keeps_excel_multiline_voucher_primary():
    table_records = [
        {"DOC_NUM": "6000004976", "COMPANY_CODE": "4020", "SAKNR": "1405020000"},
        {"DOC_NUM": "6000004976", "COMPANY_CODE": "4020", "SAKNR": "2202040000"},
    ]
    ocr_records = [
        {"DOC_NUM": "6000004976", "COMPANY_CODE": "4020", "SAKNR": "1405020000"},
        {"DOC_NUM": "7000000001", "COMPANY_CODE": "4020", "SAKNR": "6401000000"},
    ]

    kept, removed = remove_duplicate_ocr_samples(table_records, ocr_records)

    assert len(table_records) == 2
    assert [row["DOC_NUM"] for row in kept] == ["7000000001"]
    assert [row["DOC_NUM"] for row in removed] == ["6000004976"]
