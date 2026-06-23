import sys
from pathlib import Path

from openpyxl import load_workbook

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from report_generator import ReportGenerator


def test_report_generator_expands_pair_samples_to_voucher_lines(tmp_path):
    generator = ReportGenerator(tmp_path)

    path = generator.generate(
        ranked_scenarios=[{"name": "销售成本结转", "total_value": 0}],
        di_results=[
            {
                "scenario": "销售成本结转",
                "di_description": "description",
                "sample_table": {
                    "DOC_NUM": "8174291462",
                    "DATE": "2026-01-08",
                    "DEBIT_ACC": "6401000000",
                    "DEBIT_DESC": "主营业务成本",
                    "CREDIT_ACC": "1405010000",
                    "CREDIT_DESC": "库存商品-产成品",
                    "AMOUNT": 13.21,
                },
            },
            {
                "scenario": "销售成本结转",
                "di_description": "description",
                "sample_table": {
                    "DOC_NUM": "8174291462",
                    "DATE": "2026-01-08",
                    "DEBIT_ACC": "6401000000",
                    "DEBIT_DESC": "主营业务成本",
                    "CREDIT_ACC": "1405010000",
                    "CREDIT_DESC": "库存商品-产成品",
                    "AMOUNT": 54.18,
                },
            },
        ],
    )

    ws = load_workbook(path)["销售成本结转"]

    assert [ws.cell(row=27, column=col).value for col in range(4, 10)] == [
        "凭证号",
        "借贷方向",
        "科目",
        "描述",
        "金额",
        "日期",
    ]
    assert [ws.cell(row=row, column=5).value for row in range(28, 32)] == ["借方", "贷方", "借方", "贷方"]
    assert [ws.cell(row=row, column=6).value for row in range(28, 32)] == [
        "6401000000",
        "1405010000",
        "6401000000",
        "1405010000",
    ]
    assert [ws.cell(row=row, column=8).value for row in range(28, 32)] == [13.21, 13.21, 54.18, 54.18]


def test_report_generator_uses_multiline_sample_details(tmp_path):
    generator = ReportGenerator(tmp_path)

    path = generator.generate(
        ranked_scenarios=[{"name": "采购收货", "total_value": 0}],
        di_results=[
            {
                "scenario": "采购收货",
                "di_description": "description",
                "sample_table": {
                    "DOC_NUM": "6000004976",
                    "DATE": "2025-07-28",
                    "DEBIT_ACC": "1405020000; 1405050100",
                    "DEBIT_DESC": "库存商品-自制成品; 库存商品-自制成品差异-采购差异",
                    "CREDIT_ACC": "2202040000",
                    "CREDIT_DESC": "应付账款-GR/IR",
                    "AMOUNT": 598470.6,
                    "DEBIT_LINES": [
                        {"account": "1405020000", "description": "库存商品-自制成品", "amount": 528470.34},
                        {"account": "1405050100", "description": "库存商品-自制成品差异-采购差异", "amount": 70000.26},
                    ],
                    "CREDIT_LINES": [
                        {"account": "2202040000", "description": "应付账款-GR/IR", "amount": 598470.6},
                    ],
                },
            },
        ],
    )

    ws = load_workbook(path)["采购收货"]

    assert [ws.cell(row=row, column=5).value for row in range(28, 31)] == ["借方", "借方", "贷方"]
    assert [ws.cell(row=row, column=6).value for row in range(28, 31)] == [
        "1405020000",
        "1405050100",
        "2202040000",
    ]
    assert [ws.cell(row=row, column=8).value for row in range(28, 31)] == [528470.34, 70000.26, 598470.6]
