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


def test_samples_maps_audit_scenario_column(tmp_path):
    sample_path = tmp_path / "samples.csv"
    sample_path.write_text(
        "DOC_NUM,SAKNR,AMOUNT,审计场景\nS-001,1403000000,10,完工入库\n",
        encoding="utf-8-sig",
    )

    ok, msg, df = DataValidator.validate_file(MockUpload(sample_path), "Samples")

    assert ok, msg
    assert df.iloc[0]["SCENARIO"] == "完工入库"


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


def test_t030_maps_valuation_group_and_class(tmp_path):
    t030_path = tmp_path / "t030.csv"
    t030_path.write_text(
        "\n".join([
            "KTOSL,KOMOK,BWMOD,ValCl,KONTS,KONTH",
            "WRX,,1000,7900,2202040000,2202040000",
        ]),
        encoding="utf-8-sig",
    )

    ok, msg, df = DataValidator.validate_file(MockUpload(t030_path), "T030")

    assert ok, msg
    assert {"KTOSL", "KOMOK", "BWMOD", "BKLAS", "KONTS", "KONTH"}.issubset(df.columns)
    assert df.iloc[0]["BWMOD"] == "1000"
    assert df.iloc[0]["BKLAS"] == "7900"


def test_samples_maps_material_number(tmp_path):
    sample_path = tmp_path / "samples.csv"
    sample_path.write_text(
        "\n".join([
            "DOC_NUM,SAKNR,Material,AMOUNT",
            "S-001,1403000000,TX5F6609-0000,10",
        ]),
        encoding="utf-8-sig",
    )

    ok, msg, df = DataValidator.validate_file(MockUpload(sample_path), "Samples")

    assert ok, msg
    assert "MATNR" in df.columns
    assert df.iloc[0]["MATNR"] == "TX5F6609-0000"


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


def test_t001k_maps_company_valuation_area_and_group(tmp_path):
    t001k_path = tmp_path / "t001k.csv"
    t001k_path.write_text(
        "\n".join([
            "公司代码,评估范围,评估分组",
            "4000,4000,0001",
        ]),
        encoding="utf-8-sig",
    )

    ok, msg, df = DataValidator.validate_file(MockUpload(t001k_path), "T001K")

    assert ok, msg
    assert {"BUKRS", "BWKEY", "BWMOD"}.issubset(df.columns)
    assert df.iloc[0]["BUKRS"] == "4000"
    assert df.iloc[0]["BWKEY"] == "4000"
    assert df.iloc[0]["BWMOD"] == "0001"
