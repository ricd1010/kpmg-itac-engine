import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ledger_analysis import (
    analyze_ledger,
    build_exception_ledger,
    build_ledger_coverage_summary,
    classify_ledger_scenarios,
)


def _ranked():
    return [{
        "name": "采购收货",
        "raw_accounts": ["1403000000", "2202030100"],
        "amount_accounts": ["1403000000", "2202030100"],
        "account_details": [
            {
                "account": "1403000000",
                "description": "原材料",
                "direction": "借方",
                "ktosl": "WRX",
                "komok": "",
            },
            {
                "account": "2202030100",
                "description": "应付账款-GR/IR",
                "direction": "贷方",
                "ktosl": "WRX",
                "komok": "",
            },
        ],
    }]


def _t030():
    return pd.DataFrame([{
        "KTOSL": "WRX",
        "KOMOK": "",
        "BWMOD": "4110",
        "BKLAS": "3000",
        "KONTS": "1403000000",
        "KONTH": "2202030100",
    }])


def test_classify_ledger_scenarios_uses_account_and_transaction_rule():
    ledger = pd.DataFrame([{
        "DOC_NUM": "900001",
        "COMPANY_CODE": "4000",
        "SAKNR": "2202030100",
        "AMOUNT": "-100",
        "SHKZG": "H",
        "KTOSL": "WRX",
    }])

    result = classify_ledger_scenarios(ledger, _ranked())

    assert result.iloc[0]["SCENARIO"] == "采购收货"
    assert result.iloc[0]["SCENARIO_MATCH_STATUS"] == "已匹配自动化场景"


def test_analyze_ledger_marks_passed_lines_as_substantive_tested():
    ledger = pd.DataFrame([{
        "DOC_NUM": "900001",
        "COMPANY_CODE": "4000",
        "SAKNR": "2202030100",
        "MATNR": "MAT-1",
        "AMOUNT": "-100",
        "SHKZG": "H",
        "KTOSL": "WRX",
    }])
    t001k = pd.DataFrame([{"BUKRS": "4000", "BWMOD": "4110"}])
    mm03 = [{"material_number": "MAT-1", "plant": "4110", "valuation_class": "3000"}]

    result = analyze_ledger(ledger, _ranked(), _t030(), t001k, mm03)

    assert result.iloc[0]["CONFIG_VALIDATION_STATUS"] == "通过"
    assert result.iloc[0]["SUBSTANTIVE_TEST_STATUS"] == "已完成实质性测试"
    summary = build_ledger_coverage_summary(result)
    assert summary["covered_lines"] == 1
    assert summary["amount_coverage_pct"] == 100.0


def test_analyze_ledger_exports_unmatched_accounts_as_exceptions():
    ledger = pd.DataFrame([{
        "DOC_NUM": "900002",
        "COMPANY_CODE": "4000",
        "SAKNR": "9999999999",
        "AMOUNT": "200",
        "SHKZG": "S",
    }])

    result = analyze_ledger(ledger, _ranked(), _t030(), pd.DataFrame(), [])
    exceptions = build_exception_ledger(result)

    assert result.iloc[0]["SCENARIO_MATCH_STATUS"] == "无法匹配自动化场景"
    assert result.iloc[0]["SUBSTANTIVE_TEST_STATUS"] == "未完成实质性测试"
    assert exceptions.iloc[0]["异常类型"] == "无法匹配自动化场景"
