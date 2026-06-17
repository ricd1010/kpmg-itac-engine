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


def test_t030_keeps_account_modifier_separate_from_account_code():
    ok, msg, df = DataValidator.validate_file(
        MockUpload(REPO_ROOT / "data" / "xinxiwang" / "T030 HEBING.xlsx"),
        "T030",
    )

    assert ok, msg
    assert {"KTOSL", "KOMOK", "KONTS", "KONTH"}.issubset(df.columns)

    gbb_vax = df[(df["KTOSL"] == "GBB") & (df["KOMOK"] == "VAX")]
    assert not gbb_vax.empty
    assert gbb_vax["KONTS"].astype(str).str.match(r"^\d{10}$").all()


def test_trial_balance_maps_company_period_and_ytd_columns(tmp_path):
    tb_path = tmp_path / "trial_balance.csv"
    tb_path.write_text(
        "\n".join([
            "会计年度,会计期间,月份,公司代码,科目编码,科目名称,本月借方发生额,本月贷方发生额,本年借方累计,本年贷方累计",
            "2025,202501,01,4000,1403000000,原材料,10,-10,100,-100",
        ]),
        encoding="utf-8-sig",
    )

    ok, msg, df = DataValidator.validate_file(MockUpload(tb_path), "TrialBalance")

    assert ok, msg
    assert {"COMPANY_CODE", "PERIOD", "SAKNR", "TXT50", "DMBTR_DEBIT", "DMBTR_CREDIT"}.issubset(df.columns)
    assert df.iloc[0]["COMPANY_CODE"] == "4000"
    assert df.iloc[0]["PERIOD"] == "202501"
    assert df.iloc[0]["SAKNR"] == "1403000000"
    assert df.iloc[0]["DMBTR_DEBIT"] == 100.0
    assert df.iloc[0]["DMBTR_CREDIT"] == -100.0
