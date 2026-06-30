import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from voucher_validation import validate_voucher_t030_logic


def test_validate_voucher_t030_logic_passes_matching_material_and_company():
    samples = pd.DataFrame([{
        "DOC_NUM": "900001",
        "SCENARIO": "采购收货",
        "COMPANY_CODE": "4000",
        "MATNR": "MAT-1",
        "SAKNR": "2202030100",
        "SHKZG": "H",
        "KTOSL": "WRX",
    }])
    t030 = pd.DataFrame([{
        "KTOSL": "WRX",
        "KOMOK": "",
        "BWMOD": "4110",
        "BKLAS": "3000",
        "KONTS": "1403000000",
        "KONTH": "2202030100",
    }])
    t001k = pd.DataFrame([{"BUKRS": "4000", "BWMOD": "4110"}])
    mm03_records = [{"material_number": "MAT-1", "plant": "4110", "valuation_class": "3000"}]

    result = validate_voucher_t030_logic(samples, t030, t001k, mm03_records)

    assert result.iloc[0]["校验结论"] == "通过"
    assert result.iloc[0]["T030期望科目"] == "2202030100"
    assert result.iloc[0]["MM03评估分类"] == "3000"


def test_validate_voucher_t030_logic_flags_mismatched_account():
    samples = pd.DataFrame([{
        "DOC_NUM": "900002",
        "SCENARIO": "采购收货",
        "COMPANY_CODE": "4000",
        "MATNR": "MAT-1",
        "SAKNR": "9999999999",
        "SHKZG": "S",
        "KTOSL": "WRX",
    }])
    t030 = pd.DataFrame([{
        "KTOSL": "WRX",
        "BWMOD": "4110",
        "BKLAS": "3000",
        "KONTS": "1403000000",
        "KONTH": "2202030100",
    }])
    t001k = pd.DataFrame([{"BUKRS": "4000", "BWMOD": "4110"}])
    mm03_records = [{"material_number": "MAT-1", "plant": "4110", "valuation_class": "3000"}]

    result = validate_voucher_t030_logic(samples, t030, t001k, mm03_records)

    assert result.iloc[0]["校验结论"] == "不一致"
    assert result.iloc[0]["T030期望科目"] == "1403000000"


def test_validate_voucher_t030_logic_requires_company_and_material_context():
    samples = pd.DataFrame([{
        "DOC_NUM": "900003",
        "SCENARIO": "采购收货",
        "SAKNR": "1403000000",
        "SHKZG": "S",
    }])

    result = validate_voucher_t030_logic(samples, pd.DataFrame(), pd.DataFrame(), [])

    assert result.iloc[0]["校验结论"] == "待补充"
    assert "公司代码" in result.iloc[0]["校验说明"]
