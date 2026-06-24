import sys
from pathlib import Path

# Add src to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from core1_main import Core1Orchestrator
from data_validator import DataValidator


class MockUpload:
    def __init__(self, path):
        self.path = Path(path)
        self.name = self.path.name
        self._data = self.path.read_bytes()
        self._pos = 0

    def seek(self, pos):
        self._pos = pos

    def read(self, size=-1):
        if size == -1:
            chunk = self._data[self._pos:]
            self._pos = len(self._data)
            return chunk
        chunk = self._data[self._pos:self._pos + size]
        self._pos += len(chunk)
        return chunk

def test_core1_scenario_identification():
    data_dir = REPO_ROOT / "data"
    orchestrator = Core1Orchestrator(data_dir)
    results = orchestrator.run()
    
    assert len(results) == 10
    scenario_names = [res['name'] for res in results]
    assert "销售发货" in scenario_names
    
    # Check if sorting is correct (first should be larger than last)
    assert results[0]['total_value'] >= results[-1]['total_value']


def test_core1_preview_runs_without_trial_balance(tmp_path):
    fixtures = {
        "T030": REPO_ROOT / "data" / "xinxiwang" / "T030 HEBING.xlsx",
        "SKAT": REPO_ROOT / "data" / "xinxiwang" / "SKAT.xls",
    }
    for file_type, path in fixtures.items():
        ok, msg, df = DataValidator.validate_file(MockUpload(path), file_type)
        assert ok, msg
        df.to_csv(tmp_path / f"{file_type}.csv", index=False, encoding="utf-8-sig")

    results = Core1Orchestrator(tmp_path).run()

    assert len(results) == 10
    assert all(result["total_value"] == 0 for result in results)
    assert any(result["accounts"] for result in results)
    assert all(result["baseline_company_code"] is None for result in results)
    assert all(result["baseline_account_codes"] == [] for result in results)
    assert all(result["extra_account_count"] == 0 for result in results)


def test_core1_uses_last_period_per_company_for_trial_balance(tmp_path):
    (tmp_path / "T030.csv").write_text(
        "\n".join([
            "KTOSL,KOMOK,KONTS,KONTH",
            "BSX,,1403000000,1403000000",
            "WRX,,2202040000,2202040000",
        ]),
        encoding="utf-8-sig",
    )
    (tmp_path / "SKAT.csv").write_text(
        "SAKNR,TXT50\n1403000000,原材料\n2202040000,应付账款-GR/IR\n",
        encoding="utf-8-sig",
    )
    (tmp_path / "TrialBalance.csv").write_text(
        "\n".join([
            "COMPANY_CODE,PERIOD,SAKNR,TXT50,DMBTR_DEBIT,DMBTR_CREDIT,YTD_DEBIT,ENDING_BALANCE",
            "4000,202501,1403000000,原材料,1000,-1000,9999,8888",
            "4000,202502,1403000000,原材料,25,-2500,9999,8888",
            "4000,202502,1403000000,原材料,2,-200,9999,8888",
            "4000,202502,2202040000,应付账款-GR/IR,7,-700,9999,8888",
            "4010,202501,1403000000,原材料,5,-500,9999,8888",
            "4010,202503,1403000000,原材料,3,-300,9999,8888",
            "4010,202503,2202040000,应付账款-GR/IR,5,-500,9999,8888",
        ]),
        encoding="utf-8-sig",
    )

    results = Core1Orchestrator(tmp_path).run()
    purchase_receipt = next(result for result in results if result["name"] == "采购收货")
    sales_entry = next(result for result in results if result["name"] == "销售入账")

    assert purchase_receipt["raw_accounts"] == ["1403000000", "2202040000"]
    assert purchase_receipt["amount_accounts"] == ["2202040000"]
    assert purchase_receipt["total_value"] == 12.0
    assert purchase_receipt["debit_value"] == 12.0
    assert purchase_receipt["credit_value"] == 1200.0
    assert purchase_receipt["combined_value"] == 1212.0
    assert purchase_receipt["baseline_company_code"] == "4010"
    assert purchase_receipt["baseline_account_codes"] == ["2202040000"]
    assert purchase_receipt["extra_account_count"] == 0
    assert purchase_receipt["company_values"] == [
        {
            "company_code": "4000",
            "total_value": 7.0,
            "debit_value": 7.0,
            "credit_value": 700.0,
            "combined_value": 707.0,
            "account_values": [
                {
                    "account": "2202040000",
                    "description": "应付账款-GR/IR",
                    "total_value": 7.0,
                    "debit_value": 7.0,
                    "credit_value": 700.0,
                    "combined_value": 707.0,
                    "is_extra": False,
                    "baseline_company_code": "4010",
                },
            ],
        },
        {
            "company_code": "4010",
            "total_value": 5.0,
            "debit_value": 5.0,
            "credit_value": 500.0,
            "combined_value": 505.0,
            "account_values": [
                {
                    "account": "2202040000",
                    "description": "应付账款-GR/IR",
                    "total_value": 5.0,
                    "debit_value": 5.0,
                    "credit_value": 500.0,
                    "combined_value": 505.0,
                    "is_extra": False,
                    "baseline_company_code": "4010",
                },
            ],
        },
    ]
    assert sales_entry["raw_accounts"] == []
    assert sales_entry["total_value"] == 0
    assert sales_entry["company_values"] == []
    assert sales_entry["baseline_company_code"] is None
    assert sales_entry["baseline_account_codes"] == []
    assert sales_entry["extra_account_count"] == 0


def test_core1_baseline_tie_breaks_by_amount_then_company_code(tmp_path):
    (tmp_path / "T030.csv").write_text(
        "\n".join([
            "KTOSL,KOMOK,KONTS,KONTH",
            "BSX,,1403000000,1403000000",
            "WRX,,2202040000,2202040000",
            "WRX,,2221010101,2221010101",
        ]),
        encoding="utf-8-sig",
    )
    (tmp_path / "SKAT.csv").write_text(
        "SAKNR,TXT50\n1403000000,原材料\n2202040000,应付账款-GR/IR\n2221010101,进项税额\n",
        encoding="utf-8-sig",
    )
    (tmp_path / "TrialBalance.csv").write_text(
        "\n".join([
            "COMPANY_CODE,PERIOD,SAKNR,TXT50,DMBTR_DEBIT",
            "4000,202502,1403000000,原材料,100",
            "4000,202502,2202040000,应付账款-GR/IR,20",
            "4010,202502,1403000000,原材料,100",
            "4010,202502,2202040000,应付账款-GR/IR,10",
            "4020,202502,1403000000,原材料,100",
            "4020,202502,2202040000,应付账款-GR/IR,10",
            "4030,202502,1403000000,原材料,100",
            "4030,202502,2202040000,应付账款-GR/IR,10",
            "4030,202502,2221010101,进项税额,1",
        ]),
        encoding="utf-8-sig",
    )

    results = Core1Orchestrator(tmp_path).run()
    purchase_receipt = next(result for result in results if result["name"] == "采购收货")
    company_4030 = next(item for item in purchase_receipt["company_values"] if item["company_code"] == "4030")
    extra_4030 = [account for account in company_4030["account_values"] if account["is_extra"]]

    assert purchase_receipt["baseline_company_code"] == "4010"
    assert purchase_receipt["baseline_account_codes"] == ["2202040000"]
    assert purchase_receipt["extra_account_count"] == 1
    assert extra_4030 == [{
        "account": "2221010101",
        "description": "进项税额",
        "total_value": 1.0,
        "is_extra": True,
        "baseline_company_code": "4010",
    }]


def test_core1_uses_specific_amount_accounts_to_avoid_shared_bsx_duplication(tmp_path):
    (tmp_path / "T030.csv").write_text(
        "\n".join([
            "KTOSL,KOMOK,KONTS,KONTH",
            "BSX,,1403000000,1405010000",
            "WRX,,2202040000,2202040000",
            "GBB,VBO,5001010100,5001010100",
        ]),
        encoding="utf-8-sig",
    )
    (tmp_path / "SKAT.csv").write_text(
        "\n".join([
            "SAKNR,TXT50",
            "1403000000,原材料",
            "1405010000,库存商品",
            "2202040000,应付账款-GR/IR",
            "5001010100,生产成本-原材料",
        ]),
        encoding="utf-8-sig",
    )
    (tmp_path / "TrialBalance.csv").write_text(
        "\n".join([
            "COMPANY_CODE,PERIOD,SAKNR,TXT50,DMBTR_DEBIT",
            "4390,202512,1403000000,原材料,8237293.60",
            "4390,202512,1405010000,库存商品,721019.34",
            "4390,202512,2202040000,应付账款-GR/IR,100",
            "4390,202512,5001010100,生产成本-原材料,200",
        ]),
        encoding="utf-8-sig",
    )

    results = Core1Orchestrator(tmp_path).run()
    purchase_receipt = next(result for result in results if result["name"] == "采购收货")
    production_issue = next(result for result in results if result["name"] == "生产领料")

    assert set(purchase_receipt["raw_accounts"]) == {"1403000000", "1405010000", "2202040000"}
    assert purchase_receipt["amount_accounts"] == ["2202040000"]
    assert purchase_receipt["total_value"] == 100
    assert purchase_receipt["company_values"][0]["account_values"] == [{
        "account": "2202040000",
        "description": "应付账款-GR/IR",
        "total_value": 100.0,
        "is_extra": False,
        "baseline_company_code": "4390",
    }]

    assert set(production_issue["raw_accounts"]) == {"1403000000", "1405010000", "5001010100"}
    assert production_issue["amount_accounts"] == ["5001010100"]
    assert production_issue["total_value"] == 200
    assert production_issue["company_values"][0]["account_values"] == [{
        "account": "5001010100",
        "description": "生产成本-原材料",
        "total_value": 200.0,
        "is_extra": False,
        "baseline_company_code": "4390",
    }]


def test_core1_filters_completion_amount_accounts_to_completion_transfer_accounts(tmp_path):
    (tmp_path / "T030.csv").write_text(
        "\n".join([
            "KTOSL,KOMOK,KONTS,KONTH",
            "BSX,,1405020000,1405020000",
            "GBB,AUF,5001080000,5001080000",
            "GBB,AUF,5001090000,5001090000",
            "GBB,AUF,8017050000,8017050000",
        ]),
        encoding="utf-8-sig",
    )
    (tmp_path / "SKAT.csv").write_text(
        "\n".join([
            "SAKNR,TXT50",
            "1405020000,库存商品-自制成品",
            "5001080000,生产成本-半成品完工转出",
            "5001090000,生产成本-产成品完工转出",
            "8017050000,物料消耗-原材料",
        ]),
        encoding="utf-8-sig",
    )
    (tmp_path / "TrialBalance.csv").write_text(
        "\n".join([
            "COMPANY_CODE,PERIOD,SAKNR,TXT50,DMBTR_DEBIT",
            "4390,202512,1405020000,库存商品-自制成品,1000",
            "4390,202512,5001080000,生产成本-半成品完工转出,60",
            "4390,202512,5001090000,生产成本-产成品完工转出,40",
            "4390,202512,8017050000,物料消耗-原材料,59712672.98",
        ]),
        encoding="utf-8-sig",
    )

    results = Core1Orchestrator(tmp_path).run()
    completion = next(result for result in results if result["name"] == "完工入库")

    assert set(completion["raw_accounts"]) == {"1405020000", "5001080000", "5001090000", "8017050000"}
    assert completion["amount_accounts"] == ["5001080000", "5001090000"]
    assert completion["total_value"] == 100
    assert completion["company_values"][0]["account_values"] == [
        {
            "account": "5001080000",
            "description": "生产成本-半成品完工转出",
            "total_value": 60.0,
            "is_extra": False,
            "baseline_company_code": "4390",
        },
        {
            "account": "5001090000",
            "description": "生产成本-产成品完工转出",
            "total_value": 40.0,
            "is_extra": False,
            "baseline_company_code": "4390",
        },
    ]


def test_core1_keeps_prd_pra_only_in_finished_goods_variance_amounts(tmp_path):
    (tmp_path / "T030.csv").write_text(
        "\n".join([
            "KTOSL,KOMOK,KONTS,KONTH",
            "PRD,PRA,1403010200,1403010200",
            "PRD,PRF,1403010200,1403010200",
            "PRD,PRF,1403010400,1403010400",
        ]),
        encoding="utf-8-sig",
    )
    (tmp_path / "SKAT.csv").write_text(
        "\n".join([
            "SAKNR,TXT50",
            "1403010200,原材料-差异-物料转物料差异",
            "1403010400,原材料-差异-差异",
        ]),
        encoding="utf-8-sig",
    )
    (tmp_path / "TrialBalance.csv").write_text(
        "\n".join([
            "COMPANY_CODE,PERIOD,SAKNR,TXT50,DMBTR_DEBIT",
            "4390,202512,1403010200,原材料-差异-物料转物料差异,100",
            "4390,202512,1403010400,原材料-差异-差异,200",
        ]),
        encoding="utf-8-sig",
    )

    results = Core1Orchestrator(tmp_path).run()
    work_order_variance = next(result for result in results if result["name"] == "工单差异")
    finished_goods_variance = next(result for result in results if result["name"] == "产成品差异")

    assert set(work_order_variance["raw_accounts"]) == {"1403010200", "1403010400"}
    assert work_order_variance["amount_accounts"] == ["1403010400"]
    assert work_order_variance["total_value"] == 200
    assert work_order_variance["company_values"][0]["account_values"] == [{
        "account": "1403010400",
        "description": "原材料-差异-差异",
        "total_value": 200.0,
        "is_extra": False,
        "baseline_company_code": "4390",
    }]

    assert finished_goods_variance["amount_accounts"] == ["1403010200"]
    assert finished_goods_variance["total_value"] == 100
    assert finished_goods_variance["company_values"][0]["account_values"] == [{
        "account": "1403010200",
        "description": "原材料-差异-物料转物料差异",
        "total_value": 100.0,
        "is_extra": False,
        "baseline_company_code": "4390",
    }]


def test_core1_outputs_account_details_with_direction_and_valuation_fields(tmp_path):
    (tmp_path / "T030.csv").write_text(
        "\n".join([
            "KTOSL,KOMOK,BWMOD,BKLAS,KONTS,KONTH",
            "WRX,,1000,7900,1403000000,2202040000",
            "BSX,,1000,7900,1403000000,1403000000",
        ]),
        encoding="utf-8-sig",
    )
    (tmp_path / "SKAT.csv").write_text(
        "\n".join([
            "SAKNR,TXT50",
            "1403000000,原材料",
            "2202040000,应付账款-GR/IR",
        ]),
        encoding="utf-8-sig",
    )
    (tmp_path / "TrialBalance.csv").write_text(
        "\n".join([
            "COMPANY_CODE,PERIOD,SAKNR,TXT50,DMBTR_DEBIT",
            "4000,202512,2202040000,应付账款-GR/IR,50",
        ]),
        encoding="utf-8-sig",
    )

    results = Core1Orchestrator(tmp_path).run()
    purchase_receipt = next(result for result in results if result["name"] == "采购收货")
    detail_by_account = {
        detail["account"]: detail
        for detail in purchase_receipt["account_details"]
    }

    assert purchase_receipt["amount_accounts"] == ["1403000000", "2202040000"]
    assert purchase_receipt["total_value"] == 50
    assert detail_by_account["1403000000"]["direction"] == "借贷双方"
    assert detail_by_account["1403000000"]["ktosl"] == "BSX / WRX"
    assert detail_by_account["1403000000"]["bwmod"] == "1000"
    assert detail_by_account["1403000000"]["bklas"] == "7900"
    assert detail_by_account["2202040000"]["direction"] == "贷方"
    assert detail_by_account["2202040000"]["ktosl"] == "WRX"

if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
