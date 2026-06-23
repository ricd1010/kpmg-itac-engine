import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

class ReportGenerator:
    def __init__(self, output_dir):
        self.output_path = os.path.join(output_dir, "WorkingPaper_Final.xlsx")

    @staticmethod
    def _is_placeholder_account(value):
        text = str(value or "").strip()
        if not text:
            return True
        return "OCR未识别" in text or "未识别对方科目" in text

    @classmethod
    def _sample_to_toe_rows(cls, sample):
        doc_num = sample.get("DOC_NUM", "")
        date = sample.get("DATE", "N/A")
        rows = []

        for direction, key in (("借方", "DEBIT_LINES"), ("贷方", "CREDIT_LINES")):
            for line in sample.get(key) or []:
                rows.append({
                    "doc_num": doc_num,
                    "direction": direction,
                    "account": line.get("account", ""),
                    "description": line.get("description", ""),
                    "amount": line.get("amount", 0),
                    "date": date,
                })

        if rows:
            return rows

        for direction, account_key, desc_key in (
            ("借方", "DEBIT_ACC", "DEBIT_DESC"),
            ("贷方", "CREDIT_ACC", "CREDIT_DESC"),
        ):
            account = sample.get(account_key, "")
            if cls._is_placeholder_account(account):
                continue
            rows.append({
                "doc_num": doc_num,
                "direction": direction,
                "account": account,
                "description": sample.get(desc_key, ""),
                "amount": sample.get("AMOUNT", 0),
                "date": date,
            })

        if rows:
            return rows

        return [{
            "doc_num": doc_num,
            "direction": "",
            "account": sample.get("DEBIT_ACC", ""),
            "description": sample.get("DEBIT_DESC", ""),
            "amount": sample.get("AMOUNT", 0),
            "date": date,
        }]

    def generate(self, ranked_scenarios, di_results, audit_context=None):
        if audit_context is None:
            audit_context = {}

        wb = Workbook()
        
        # 1. Summary Sheet
        ws_summary = wb.active
        ws_summary.title = "审计总览"
        
        # Style Definitions
        kpmg_blue_fill = PatternFill(start_color="00338D", end_color="00338D", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

        # Title
        ws_summary.merge_cells("A1:E1")
        ws_summary["A1"] = "自动化控制 (ITAC) 审计测试总览表"
        ws_summary["A1"].font = Font(size=16, bold=True, color="00338D")
        ws_summary["A1"].alignment = align_center

        # Headers
        table_headers = ["控制编号", "审计场景 / 流程活动", "控制属性", "涉及金额 (本年余额)", "审计穿行结论"]
        ws_summary.append(table_headers)
        for cell in ws_summary[ws_summary.max_row]:
            cell.font = header_font
            cell.fill = kpmg_blue_fill
            cell.alignment = align_center
            cell.border = thin_border

        # Data
        di_map = {}
        for res in di_results:
            name = res['scenario']
            if name not in di_map: di_map[name] = []
            di_map[name].append(res)

        for res in ranked_scenarios:
            name = res['name']
            samples = di_map.get(name, [])
            conclusion = f"通过 ({len(samples)}个样本)" if samples else "未匹配到样本"
            row = ["ITAC_CTRL", name, "Automated", f"{res['total_value']:,.2f}", conclusion]
            ws_summary.append(row)
            for cell in ws_summary[ws_summary.max_row]:
                cell.border = thin_border
        
        ws_summary.column_dimensions['A'].width = 15
        ws_summary.column_dimensions['B'].width = 50
        ws_summary.column_dimensions['D'].width = 20
        ws_summary.column_dimensions['E'].width = 25

        # 1.5 WGLL Sheet (Methodology)
        ws_wgll = wb.create_sheet("方法论与较佳实践 (WGLL)")
        ws_wgll["A1"] = "毕马威 ITAC 审计方法论指导"
        ws_wgll["A1"].font = Font(size=14, bold=True)
        guidelines = [
            "1. ITAC (Information Technology Application Controls) 是嵌入在 ERP 系统中的自动化控制。",
            "2. 本工具通过解析 T030 等配置表，识别 SAP 系统中预设的自动记账逻辑。",
            "3. 场景识别基于会计科目与业务流程的映射（Mapping）。",
            "4. 穿行测试描述（D&I）由 AI 根据识别出的具体凭证行项目自动撰写。",
            "5. 审计人员应核对 AI 生成的描述是否与企业的实际 IPE（信息产生的流程）一致。"
        ]
        for i, text in enumerate(guidelines):
            ws_wgll.cell(row=i+3, column=1, value=text)
        ws_wgll.column_dimensions['A'].width = 100

        # 2. Detailed D&I Sheets (Based on Standard Template)
        for scenario_name, results in di_map.items():
            # Create a safe sheet name
            safe_title = "".join([c for c in scenario_name if c.isalnum() or c==' '])[:31].strip()
            ws = wb.create_sheet(title=safe_title)
            
            # Formatting as per template
            ws.column_dimensions['D'].width = 15
            ws.column_dimensions['E'].width = 30
            ws.column_dimensions['F'].width = 15
            ws.column_dimensions['G'].width = 15
            ws.column_dimensions['H'].width = 60
            ws.column_dimensions['I'].width = 15

            # Row 2: Header
            ws.merge_cells("D2:H2")
            ws["D2"] = "设计和执行(D&I)"
            ws["D2"].font = Font(size=14, bold=True)
            ws["D2"].alignment = Alignment(horizontal="center")

            # Row 3: Sub-header
            ws.merge_cells("D3:H3")
            ws["D3"] = "了解流程控制活动 / Understand the process control activities"
            ws["D3"].font = Font(bold=True)
            ws["D3"].alignment = Alignment(horizontal="center")

            # Row 6: Control Label
            ws["D6"] = "控制 / Control"
            ws["D6"].fill = kpmg_blue_fill
            ws["D6"].font = header_font
            ws["D6"].border = thin_border

            # Row 8: Control ID and Description
            ws["D8"] = "ITAC_GEN" # Placeholder ID
            ws["D8"].border = thin_border
            ws["E8"] = scenario_name
            ws["E8"].border = thin_border
            ws["E8"].alignment = Alignment(wrap_text=True)

            # Row 17: Table Headers
            cols = ["D", "E", "F", "G", "H"]
            headers = ["流程风险点 / PRP ID", "流程风险点 / PRP(s)", "重大错报风险 / RMM", "信息 / Information", "该流程控制活动如何应对流程风险点(PRP)"]
            for col, text in zip(cols, headers):
                ws[f"{col}17"] = text
                ws[f"{col}17"].fill = kpmg_blue_fill
                ws[f"{col}17"].font = Font(bold=True, color="FFFFFF", size=9)
                ws[f"{col}17"].alignment = align_center
                ws[f"{col}17"].border = thin_border

            # Row 18: TOD Narrative (Use first sample's D&I text)
            ws[f"D18"] = "PRP_01"
            ws[f"H18"] = results[0]['di_description']
            ws[f"H18"].alignment = Alignment(wrap_text=True, vertical="top")
            for col in cols: ws[f"{col}18"].border = thin_border

            # Row 20 & 22: Nature and Type
            ws["D20"] = "性质 / Nature"
            ws["D20"].fill = kpmg_blue_fill
            ws["D20"].font = header_font
            ws["E20"] = "自动化【AUTOMATED】"
            ws["D22"] = "类型 / Type"
            ws["D22"].fill = kpmg_blue_fill
            ws["D22"].font = header_font
            ws["E22"] = "预防性【PREVENTIVE】"
            ws["D20"].border = ws["E20"].border = ws["D22"].border = ws["E22"].border = thin_border

            # TOE Section (Sample List) below the D&I grid
            start_row = 26
            ws.cell(row=start_row, column=4, value="二、测试样本明细 (TOE)").font = Font(bold=True)
            headers_toe = ["凭证号", "借贷方向", "科目", "描述", "金额", "日期"]
            for i, h in enumerate(headers_toe):
                cell = ws.cell(row=start_row+1, column=4+i, value=h)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="E5E5E5", end_color="E5E5E5", fill_type="solid")
                cell.border = thin_border
            
            row_idx = start_row + 2
            for res in results:
                s = res['sample_table']
                for toe_row in self._sample_to_toe_rows(s):
                    values = [
                        toe_row["doc_num"],
                        toe_row["direction"],
                        toe_row["account"],
                        toe_row["description"],
                        toe_row["amount"],
                        toe_row["date"],
                    ]
                    for offset, value in enumerate(values):
                        cell = ws.cell(row=row_idx, column=4+offset, value=value)
                        cell.border = thin_border
                        cell.alignment = Alignment(wrap_text=True, vertical="top")
                    row_idx += 1

        wb.save(self.output_path)
        return self.output_path
