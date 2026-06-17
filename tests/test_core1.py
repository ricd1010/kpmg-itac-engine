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

if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
