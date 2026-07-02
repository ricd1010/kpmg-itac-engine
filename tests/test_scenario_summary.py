import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from scenario_summary import amount_for_direction, build_scenario_account_totals


def test_amount_for_direction_uses_balance_amount_fields():
    account = {
        "total_value": 10.0,
        "debit_value": 10.0,
        "credit_value": 3.0,
        "combined_value": 13.0,
    }

    assert amount_for_direction(account, "全部") == 13.0
    assert amount_for_direction(account, "借方") == 10.0
    assert amount_for_direction(account, "贷方") == 3.0


def test_build_scenario_account_totals_sums_same_account_across_companies():
    ranked = [{
        "name": "采购收货",
        "account_details": [{
            "account": "1403000000",
            "description": "原材料",
            "direction": "借方",
            "ktosl": "BSX",
            "komok": "",
            "bwmod": "1000",
            "bklas": "7900",
        }],
        "company_values": [
            {
                "company_code": "4000",
                "account_values": [
                    {"account": "1403000000", "description": "原材料", "total_value": 10.0},
                    {"account": "2202040000", "description": "应付账款-GR/IR", "total_value": 5.0},
                ],
            },
            {
                "company_code": "4010",
                "account_values": [
                    {"account": "1403000000", "description": "原材料", "total_value": 7.0},
                ],
            },
        ],
    }]

    rows = build_scenario_account_totals(ranked)

    raw_material = next(row for row in rows if row["account"] == "1403000000")
    gr_ir = next(row for row in rows if row["account"] == "2202040000")
    assert raw_material["scenario"] == "采购收货"
    assert "direction" not in raw_material
    assert "bwmod" not in raw_material
    assert "bklas" not in raw_material
    assert raw_material["total_value"] == 17.0
    assert raw_material["debit_value"] == 17.0
    assert raw_material["credit_value"] == 0.0
    assert raw_material["scenario_total_value"] == 22.0
    assert round(raw_material["amount_share_pct"], 2) == 77.27
    assert raw_material["company_count"] == 2
    assert raw_material["company_codes"] == ["4000", "4010"]
    assert raw_material["company_amounts"] == [
        {"company_code": "4000", "debit_value": 10.0, "credit_value": 0.0, "total_value": 10.0},
        {"company_code": "4010", "debit_value": 7.0, "credit_value": 0.0, "total_value": 7.0},
    ]
    assert gr_ir["total_value"] == 5.0
    assert gr_ir["debit_value"] == 5.0
    assert gr_ir["credit_value"] == 0.0
    assert gr_ir["scenario_total_value"] == 22.0
    assert round(gr_ir["amount_share_pct"], 2) == 22.73
    assert gr_ir["company_count"] == 1


def test_build_scenario_account_totals_ignores_empty_company_values():
    ranked = [
        {"name": "销售发票校验", "company_values": []},
        {"name": "收款核销"},
    ]

    assert build_scenario_account_totals(ranked) == []


def test_build_scenario_account_totals_filters_by_balance_direction_amounts():
    ranked = [{
        "name": "采购收货",
        "account_details": [
            {"account": "1403000000", "description": "原材料", "direction": "借方"},
            {"account": "2202040000", "description": "应付账款-GR/IR", "direction": "贷方"},
            {"account": "9999999999", "description": "双边科目", "direction": "借贷双方"},
        ],
        "company_values": [{
            "company_code": "4000",
            "account_values": [
                {
                    "account": "1403000000",
                    "description": "原材料",
                    "total_value": 10.0,
                    "debit_value": 10.0,
                    "credit_value": 1.0,
                    "combined_value": 11.0,
                },
                {
                    "account": "2202040000",
                    "description": "应付账款-GR/IR",
                    "total_value": 20.0,
                    "debit_value": 20.0,
                    "credit_value": 7.0,
                    "combined_value": 27.0,
                },
                {
                    "account": "9999999999",
                    "description": "双边科目",
                    "total_value": 30.0,
                    "debit_value": 30.0,
                    "credit_value": 2.0,
                    "combined_value": 32.0,
                },
            ],
        }],
    }]

    all_rows = build_scenario_account_totals(ranked, direction_filter="全部")
    debit_rows = build_scenario_account_totals(ranked, direction_filter="借方")
    credit_rows = build_scenario_account_totals(ranked, direction_filter="贷方")

    assert {row["account"] for row in all_rows} == {"1403000000", "2202040000", "9999999999"}
    assert {row["account"] for row in debit_rows} == {"1403000000", "2202040000", "9999999999"}
    assert {row["account"] for row in credit_rows} == {"1403000000", "2202040000", "9999999999"}

    all_gr_ir = next(row for row in all_rows if row["account"] == "2202040000")
    debit_raw_material = next(row for row in debit_rows if row["account"] == "1403000000")
    credit_gr_ir = next(row for row in credit_rows if row["account"] == "2202040000")

    assert all_gr_ir["total_value"] == 27.0
    assert all_gr_ir["debit_value"] == 20.0
    assert all_gr_ir["credit_value"] == 7.0
    assert all_gr_ir["scenario_total_value"] == 70.0
    assert all_gr_ir["company_amounts"] == [
        {"company_code": "4000", "debit_value": 20.0, "credit_value": 7.0, "total_value": 27.0},
    ]
    assert round(all_gr_ir["amount_share_pct"], 2) == 38.57
    assert debit_raw_material["scenario_total_value"] == 60.0
    assert round(debit_raw_material["amount_share_pct"], 2) == 16.67
    assert credit_gr_ir["scenario_total_value"] == 10.0
    assert round(credit_gr_ir["amount_share_pct"], 2) == 70.0
