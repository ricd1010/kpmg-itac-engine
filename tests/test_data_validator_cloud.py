import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

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


def test_trial_balance_numeric_amount_columns_are_replaced_safely(tmp_path):
    tb_path = tmp_path / "trial_balance_numeric.xlsx"
    tb_df = pd.DataFrame([
        {
            "Company Code": "4110",
            "Period": "202512",
            "G/L Account": "1403999999",
            "Short Text": "Raw material variance",
            "Debit Amount": 643776700.12,
            "Credit Amount": 536920400.34,
        },
        {
            "Company Code": "4390",
            "Period": "202512",
            "G/L Account": "1407999999",
            "Short Text": "Semi-finished variance",
            "Debit Amount": 24679890.56,
            "Credit Amount": 0.0,
        },
    ])
    tb_df.to_excel(tb_path, index=False)

    ok, msg, df = DataValidator.validate_file(MockUpload(tb_path), "TrialBalance")

    assert ok, msg
    assert list(df["COMPANY_CODE"]) == ["4110", "4390"]
    assert list(df["SAKNR"]) == ["1403999999", "1407999999"]
    assert df["DMBTR_DEBIT"].dtype.kind == "f"
    assert df.iloc[0]["DMBTR_DEBIT"] == 643776700.12
    assert df.iloc[0]["DMBTR_CREDIT"] == 536920400.34
