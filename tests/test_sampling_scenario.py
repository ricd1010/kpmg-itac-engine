import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sampling_scenario import build_sampling_scenario_table


def test_sampling_scenario_table_enriches_company_with_t001k():
    ranked = [{
        "name": "完工入库",
        "baseline_company_code": "4000",
        "company_values": [{
            "company_code": "4000",
            "total_value": 100.0,
            "account_values": [{
                "account": "5001080000",
                "description": "生产成本-半成品完工转出",
                "total_value": 100.0,
                "is_extra": False,
            }],
        }],
    }]
    t001k = pd.DataFrame([{
        "BWKEY": "4000",
        "BUKRS": "4000",
        "BWMOD": "0001",
    }])

    df = build_sampling_scenario_table(ranked, t001k, ["mm03.png"])

    assert len(df) == 1
    row = df.iloc[0]
    assert row["公司代码"] == "4000"
    assert row["评估范围"] == "4000"
    assert row["评估分组"] == "0001"
    assert row["审计场景"] == "完工入库"
    assert row["科目编码"] == "5001080000"
    assert row["科目金额"] == 100.0
    assert row["MM03截图状态"] == "已上传 1 张"


def test_sampling_scenario_table_marks_extra_accounts():
    ranked = [{
        "name": "工单差异",
        "baseline_company_code": "4000",
        "company_values": [{
            "company_code": "4100",
            "total_value": 300.0,
            "account_values": [{
                "account": "1405050100",
                "description": "库存商品-自制成品差异-采购差异",
                "total_value": 300.0,
                "is_extra": True,
            }],
        }],
    }]

    df = build_sampling_scenario_table(ranked)

    assert df.iloc[0]["是否额外科目"] == "是"
    assert "优先抽样" in df.iloc[0]["抽样建议"]


def test_sampling_scenario_table_supports_step2_preview_without_balance():
    ranked = [{
        "name": "采购收货",
        "accounts": ["1403000000 (原材料)"],
        "total_value": 0,
    }]

    df = build_sampling_scenario_table(ranked)

    assert len(df) == 1
    assert df.iloc[0]["审计场景"] == "采购收货"
    assert df.iloc[0]["科目编码"] == "1403000000"
    assert df.iloc[0]["科目描述"] == "原材料"
    assert df.iloc[0]["MM03截图状态"] == "待补充"
