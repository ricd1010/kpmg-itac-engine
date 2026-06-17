import sys
from pathlib import Path

# Add src to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from core1_main import Core1Orchestrator

def test_core1_scenario_identification():
    data_dir = REPO_ROOT / "data"
    orchestrator = Core1Orchestrator(data_dir)
    results = orchestrator.run()
    
    assert len(results) > 0
    scenario_names = [res['name'] for res in results]
    assert "销售发货" in scenario_names
    
    # Check if sorting is correct (first should be larger than last)
    assert results[0]['total_value'] >= results[-1]['total_value']

if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
