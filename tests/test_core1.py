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


def test_core1_uses_last_period_per_company_for_trial_balance(tmp_path):
    (tmp_path / "T030.csv").write_text(
        "KTOSL,KOMOK,KONTS,KONTH\nBSX,,1403000000,2202040000\n",
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
        ]),
        encoding="utf-8-sig",
    )

    results = Core1Orchestrator(tmp_path).run()
    purchase_receipt = next(result for result in results if result["name"] == "采购收货")
    sales_entry = next(result for result in results if result["name"] == "销售入账")

    assert purchase_receipt["total_value"] == 37.0
    assert purchase_receipt["company_values"] == [
        {
            "company_code": "4000",
            "total_value": 34.0,
            "account_values": [
                {"account": "1403000000", "description": "原材料", "total_value": 27.0},
                {"account": "2202040000", "description": "应付账款-GR/IR", "total_value": 7.0},
            ],
        },
        {
            "company_code": "4010",
            "total_value": 3.0,
            "account_values": [
                {"account": "1403000000", "description": "原材料", "total_value": 3.0},
            ],
        },
    ]
    assert sales_entry["raw_accounts"] == []
    assert sales_entry["total_value"] == 0
    assert sales_entry["company_values"] == []

if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
