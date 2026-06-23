import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from core2_main import Core2Orchestrator


class FakeLLM:
    def generate_text(self, system_prompt, user_prompt):
        return f"generated: {user_prompt[:40]}"


def write_samples(tmp_path, rows):
    pd.DataFrame(rows).to_csv(tmp_path / "Samples.csv", index=False, encoding="utf-8-sig")


def test_core2_generates_description_from_single_ocr_line(tmp_path):
    write_samples(tmp_path, [{
        "DOC_NUM": "OCR-001",
        "SAKNR": "1403000000",
        "TXT50": "原材料",
        "AMOUNT": "1,234.50",
        "SHKZG": "",
        "DATE": "2026-06-01",
    }])
    orchestrator = Core2Orchestrator(tmp_path)
    orchestrator.llm_client = FakeLLM()

    results = orchestrator.generate_di_descriptions([{
        "name": "采购收货",
        "accounts": ["1403000000 (原材料)"],
    }])

    assert len(results) == 1
    sample = results[0]["sample_table"]
    assert sample["DOC_NUM"] == "OCR-001"
    assert sample["DEBIT_ACC"] == "1403000000"
    assert sample["CREDIT_ACC"] == Core2Orchestrator.COUNTERPARTY_PLACEHOLDER
    assert sample["AMOUNT"] == 1234.5
    assert sample["OCR_FALLBACK"] is True
    assert results[0]["di_description"].startswith("generated:")


def test_core2_infers_credit_direction_for_negative_ocr_amount(tmp_path):
    write_samples(tmp_path, [{
        "DOC_NUM": "OCR-002",
        "SAKNR": "2202040000",
        "TXT50": "应付账款-GR/IR",
        "AMOUNT": "-88",
        "SHKZG": "",
        "DATE": "2026-06-02",
    }])
    orchestrator = Core2Orchestrator(tmp_path)
    orchestrator.llm_client = FakeLLM()

    results = orchestrator.generate_di_descriptions([{
        "name": "采购入账",
        "accounts": ["2202040000 (应付账款-GR/IR)"],
    }])

    assert len(results) == 1
    sample = results[0]["sample_table"]
    assert sample["DEBIT_ACC"] == Core2Orchestrator.COUNTERPARTY_PLACEHOLDER
    assert sample["CREDIT_ACC"] == "2202040000"
    assert sample["AMOUNT"] == 88.0


def test_core2_keeps_balanced_pair_logic(tmp_path):
    write_samples(tmp_path, [
        {
            "DOC_NUM": "PAIR-001",
            "SAKNR": "1403000000",
            "TXT50": "原材料",
            "AMOUNT": "500",
            "SHKZG": "S",
            "DATE": "2026-06-03",
        },
        {
            "DOC_NUM": "PAIR-001",
            "SAKNR": "2202040000",
            "TXT50": "应付账款-GR/IR",
            "AMOUNT": "500",
            "SHKZG": "H",
            "DATE": "2026-06-03",
        },
    ])
    orchestrator = Core2Orchestrator(tmp_path)
    orchestrator.llm_client = FakeLLM()

    results = orchestrator.generate_di_descriptions([{
        "name": "采购收货",
        "accounts": ["1403000000 (原材料)"],
    }])

    assert len(results) == 1
    sample = results[0]["sample_table"]
    assert sample["DEBIT_ACC"] == "1403000000"
    assert sample["CREDIT_ACC"] == "2202040000"
    assert "OCR_FALLBACK" not in sample


def test_core2_respects_explicit_sample_scenario(tmp_path):
    write_samples(tmp_path, [{
        "DOC_NUM": "SCN-001",
        "SAKNR": "1403000000",
        "TXT50": "Shared account",
        "AMOUNT": "100",
        "SHKZG": "S",
        "DATE": "2026-06-04",
        "SCENARIO": "Completion",
    }])
    orchestrator = Core2Orchestrator(tmp_path)
    orchestrator.llm_client = FakeLLM()

    results = orchestrator.generate_di_descriptions([
        {"name": "Purchase", "accounts": ["1403000000 (Shared account)"]},
        {"name": "Completion", "accounts": ["1403000000 (Shared account)"]},
    ])

    assert [item["scenario"] for item in results] == ["Completion"]
    assert results[0]["sample_table"]["SCENARIO"] == "Completion"


def test_core2_balances_multi_line_sap_voucher_with_trailing_credit_minus(tmp_path):
    write_samples(tmp_path, [
        {
            "DOC_NUM": "6000004976",
            "SAKNR": "1405020000",
            "TXT50": "库存商品-自制成品",
            "AMOUNT": "528.470,34",
            "SHKZG": "",
            "DATE": "2025-07-28",
        },
        {
            "DOC_NUM": "6000004976",
            "SAKNR": "1405050100",
            "TXT50": "库存商品-自制成品差异-采购差异",
            "AMOUNT": "70.000,26",
            "SHKZG": "",
            "DATE": "2025-07-28",
        },
        {
            "DOC_NUM": "6000004976",
            "SAKNR": "2202040000",
            "TXT50": "应付账款-GR/IR",
            "AMOUNT": "598.470,60-",
            "SHKZG": "",
            "DATE": "2025-07-28",
        },
    ])
    orchestrator = Core2Orchestrator(tmp_path)
    orchestrator.llm_client = FakeLLM()

    results = orchestrator.generate_di_descriptions([{
        "name": "采购收货",
        "accounts": [
            "1405020000 (库存商品-自制成品)",
            "1405050100 (库存商品-自制成品差异-采购差异)",
            "2202040000 (应付账款-GR/IR)",
        ],
    }])

    assert len(results) == 1
    sample = results[0]["sample_table"]
    assert sample["BALANCED_MATCH"] is True
    assert "OCR_FALLBACK" not in sample
    assert sample["DEBIT_ACC"] == "1405020000; 1405050100"
    assert sample["CREDIT_ACC"] == "2202040000"
    assert sample["AMOUNT"] == 598470.6
    assert sample["DEBIT_LINES"] == [
        {"account": "1405020000", "description": "库存商品-自制成品", "amount": 528470.34},
        {"account": "1405050100", "description": "库存商品-自制成品差异-采购差异", "amount": 70000.26},
    ]
    assert sample["CREDIT_LINES"] == [
        {"account": "2202040000", "description": "应付账款-GR/IR", "amount": 598470.6},
    ]


def test_normalize_samples_dataframe_removes_blank_docs_and_infers_direction():
    df = pd.DataFrame([
        {"DOC_NUM": "  ", "SAKNR": "1403000000", "AMOUNT": "1", "SHKZG": ""},
        {"DOC_NUM": "A", "SAKNR": "0001403000000", "AMOUNT": "(9)", "SHKZG": None},
    ])

    normalized = Core2Orchestrator.normalize_samples_dataframe(df)

    assert len(normalized) == 1
    row = normalized.iloc[0]
    assert row["DOC_NUM"] == "A"
    assert row["SAKNR_CLEAN"] == "1403000000"
    assert row["SHKZG"] == "H"
    assert row["AMT_VAL"] == 9.0


def test_parse_signed_amount_supports_sap_formats():
    assert Core2Orchestrator._parse_signed_amount("528,470.34") == 528470.34
    assert Core2Orchestrator._parse_signed_amount("528.470,34") == 528470.34
    assert Core2Orchestrator._parse_signed_amount("598,470.60-") == -598470.6
    assert Core2Orchestrator._parse_signed_amount("598.470,60-") == -598470.6
    assert Core2Orchestrator._parse_signed_amount("(598,470.60)") == -598470.6
