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


def test_inf_sample_excel_maps_purchase_document_as_doc_num():
    ok, msg, df = DataValidator.validate_file(
        MockUpload(REPO_ROOT / "data" / "xinxiwang" / "inf 1.XLSX"),
        "Samples",
    )

    assert ok, msg
    assert {"DOC_NUM", "SAKNR", "TXT50", "AMOUNT", "SHKZG", "KTOSL"}.issubset(df.columns)
    assert df.iloc[0]["DOC_NUM"] == "8174291462"
    assert df.iloc[0]["SAKNR"] == "1405010000"
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


def test_trial_balance_maps_company_period_and_monthly_debit_columns(tmp_path):
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
    assert df.iloc[0]["DMBTR_DEBIT"] == 10.0
    assert df.iloc[0]["DMBTR_CREDIT"] == -10.0


def test_trial_balance_excel_reads_first_sheet_only(tmp_path):
    tb_path = tmp_path / "trial_balance.xlsx"
    first_sheet = pd.DataFrame([{
        "会计年度": "2025",
        "会计期间": "202512",
        "月份": "12",
        "公司代码": "4000",
        "科目编码": "1403000000",
        "科目名称": "原材料",
        "本月借方发生额": 12,
        "本月贷方发生额": -99,
        "本年借方累计": 1200,
        "本年贷方累计": -9900,
    }])
    second_sheet = pd.DataFrame([{
        "会计年度": "2025",
        "会计期间": "202512",
        "月份": "12",
        "公司代码": "9999",
        "科目编码": "9999999999",
        "科目名称": "错误汇总页",
        "本月借方发生额": 999999,
        "本月贷方发生额": 0,
    }])
    with pd.ExcelWriter(tb_path) as writer:
        first_sheet.to_excel(writer, sheet_name="科目余额表", index=False)
        second_sheet.to_excel(writer, sheet_name="公司汇总", index=False)

    ok, msg, df = DataValidator.validate_file(MockUpload(tb_path), "TrialBalance")

    assert ok, msg
    assert len(df) == 1
    assert df.iloc[0]["COMPANY_CODE"] == "4000"
    assert df.iloc[0]["SAKNR"] == "1403000000"
    assert df.iloc[0]["DMBTR_DEBIT"] == 12.0
