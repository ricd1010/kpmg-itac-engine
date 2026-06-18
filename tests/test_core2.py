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
