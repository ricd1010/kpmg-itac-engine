import sys
from pathlib import Path

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

    def getvalue(self):
        return self._data


def test_samples_csv_is_accepted():
    ok, msg, df = DataValidator.validate_file(
        MockUpload(REPO_ROOT / "data" / "Samples.csv"),
        "Samples",
    )

    assert ok, msg
    assert {"DOC_NUM", "SAKNR", "AMOUNT"}.issubset(df.columns)
    assert df.iloc[0]["DOC_NUM"] == "1000001"
    assert df.iloc[0]["AMOUNT"] == 50000.0


def test_wide_samples_csv_is_accepted():
    ok, msg, df = DataValidator.validate_file(
        MockUpload(REPO_ROOT / "data" / "test_run" / "Samples.csv"),
        "Samples",
    )

    assert ok, msg
    assert {"DOC_NUM", "SAKNR", "AMOUNT", "KTOSL"}.issubset(df.columns)
    assert df.iloc[0]["DOC_NUM"] == "8174291462"
    assert df.iloc[0]["AMOUNT"] == -13.21
