import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sampling_scenario import build_sampling_scenario_table


def test_sampling_scenario_table_enriches_company_with_t001k():
    ranked = [{
        "name": "完工入库",
        "account_details": [{
            "account": "5001080000",
            "description": "生产成本-半成品完工转出",
            "direction": "贷方",
            "ktosl": "GBB",
            "komok": "AUF",
            "bwmod": "1000",
            "bklas": "7900",
        }],
        "company_values": [{
            "company_code": "4000",
            "total_value": 100.0,
            "account_values": [{
                "account": "5001080000",
                "description": "生产成本-半成品完工转出",
                "total_value": 100.0,
            }],
        }],
    }]
    t001k = pd.DataFrame([{
        "BUKRS": "4000",
        "BWMOD": "4110",
    }])

    mm03_records = [{
        "source_file": "MM03采购.png",
        "material_number": "10000000",
        "plant": "4110",
        "valuation_class": "3000",
    }]

    df = build_sampling_scenario_table(ranked, t001k, ["mm03.png"], mm03_records=mm03_records)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["公司代码"] == "4000"
    assert row["T001K评估分组代码"] == "4110"
    assert row["审计场景"] == "完工入库"
    assert row["科目编码"] == "5001080000"
    assert row["科目金额"] == 100.0
    assert row["占比"] == "100.00%"
    assert row["MM03截图状态"] == "匹配 1 张"
    assert row["MM03物料号"] == "10000000"
    assert row["MM03工厂编号"] == "4110"
    assert row["MM03评估分类"] == "3000"
    assert "评估范围" not in df.columns
    assert "MM03匹配截图" not in df.columns
    assert "MM03物料描述" not in df.columns
    assert "MM03价格控制" not in df.columns
    assert "配置借贷方" not in df.columns
    assert "事务码" not in df.columns
    assert "科目修改" not in df.columns
    assert "T030评估分组" not in df.columns
    assert "评估类" not in df.columns


def test_sampling_scenario_table_no_longer_exposes_extra_account_columns():
    ranked = [{
        "name": "工单差异",
        "company_values": [{
            "company_code": "4100",
            "total_value": 300.0,
            "account_values": [{
                "account": "1405050100",
                "description": "库存商品-自制成品差异-采购差异",
                "total_value": 300.0,
            }],
        }],
    }]

    df = build_sampling_scenario_table(ranked)

    assert "是否额外科目" not in df.columns
    assert "基准公司" not in df.columns
    assert df.iloc[0]["抽样建议"] == "按场景金额、科目占比和样本覆盖情况抽样"


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


def test_sampling_scenario_table_matches_multiple_mm03_records_with_fuzzy_plant():
    ranked = [{
        "name": "生产领料",
        "company_values": [{
            "company_code": "4000",
            "total_value": 500.0,
            "account_values": [{
                "account": "5001010000",
                "description": "生产成本-原辅料",
                "total_value": 500.0,
            }],
        }],
    }]
    t001k = pd.DataFrame([{
        "BUKRS": "4000",
        "BWMOD": "4110",
    }])
    mm03_records = [
        {
            "source_file": "MM03采购.png",
            "material_number": "10000000",
            "plant": "410",
            "valuation_class": "3000",
        },
        {
            "source_file": "MM03销售.png",
            "material_number": "50006420",
            "plant": "410",
            "valuation_class": "7921",
        },
    ]

    df = build_sampling_scenario_table(
        ranked,
        t001k,
        ["MM03采购.png", "MM03销售.png"],
        mm03_records=mm03_records,
    )

    row = df.iloc[0]
    assert row["T001K评估分组代码"] == "4110"
    assert row["占比"] == "100.00%"
    assert row["MM03截图状态"] == "匹配 2 张"
    assert row["MM03物料号"] == "10000000；50006420"
    assert row["MM03工厂编号"] == "4110"
    assert row["MM03评估分类"] == "3000；7921"


def test_sampling_scenario_table_ignores_dirty_session_state_records():
    ranked = [{
        "name": "生产领料",
        "company_values": [{
            "company_code": "4000",
            "total_value": {"stale": "bad"},
            "account_values": [{
                "account": ["5001010000"],
                "description": "生产成本-原辅料",
                "total_value": [],
            }],
        }],
    }]
    mm03_records = [
        object(),
        {
            "source_file": "MM03采购.png",
            "material_number": ["10000000"],
            "plant": ["4000"],
            "valuation_class": ["3000"],
        },
    ]

    df = build_sampling_scenario_table(
        ranked,
        t001k_df=object(),
        mm03_image_names=object(),
        mm03_records=mm03_records,
    )

    row = df.iloc[0]
    assert row["科目金额"] == 0.0
    assert row["场景金额"] == 0.0
    assert row["MM03截图状态"] == "匹配 1 张"
    assert row["MM03物料号"] == "10000000"
    assert row["MM03工厂编号"] == "4000"
    assert row["MM03评估分类"] == "3000"


def test_sampling_scenario_table_account_share_uses_scenario_total():
    ranked = [{
        "name": "产成品差异",
        "company_values": [{
            "company_code": "4000",
            "total_value": 100.0,
            "account_values": [
                {"account": "1403010200", "description": "原材料差异", "total_value": 80.0},
                {"account": "1409030200", "description": "半成品差异", "total_value": 20.0},
            ],
        }],
    }]

    df = build_sampling_scenario_table(ranked)

    shares = dict(zip(df["科目编码"], df["占比"]))
    assert shares["1403010200"] == "80.00%"
    assert shares["1409030200"] == "20.00%"
