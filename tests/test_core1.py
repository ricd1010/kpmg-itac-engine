import sys
import os
import pytest

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core1_main import Core1Orchestrator

def test_core1_scenario_identification():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    orchestrator = Core1Orchestrator(data_dir)
    results = orchestrator.run()
    
    assert len(results) > 0
    # Check if "销售发货" (2.1.1) is identified
    scenario_names = [res['name'] for res in results]
    assert any("2.1.1 销售发货" in name for name in scenario_names)
    
    # Check if sorting is correct (first should be larger than last)
    assert results[0]['total_value'] >= results[-1]['total_value']

if __name__ == "__main__":
    pytest.main([__file__])
