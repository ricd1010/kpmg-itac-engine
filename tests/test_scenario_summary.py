import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from scenario_summary import build_scenario_account_totals


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
                    {"account": "2202040000", "description": "应付账款-GR/IR", "total_value": 5.0, "is_extra": True},
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
    assert raw_material["scenario_total_value"] == 22.0
    assert round(raw_material["amount_share_pct"], 2) == 77.27
    assert raw_material["company_count"] == 2
    assert raw_material["company_codes"] == ["4000", "4010"]
    assert gr_ir["total_value"] == 5.0
    assert gr_ir["scenario_total_value"] == 22.0
    assert round(gr_ir["amount_share_pct"], 2) == 22.73
    assert gr_ir["company_count"] == 1
    assert gr_ir["extra_company_count"] == 1


def test_build_scenario_account_totals_ignores_empty_company_values():
    ranked = [
        {"name": "销售入账", "company_values": []},
        {"name": "收款核销"},
    ]

    assert build_scenario_account_totals(ranked) == []
