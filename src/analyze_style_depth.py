import pandas as pd
import openpyxl

def analyze_template_style(path):
    print(f"--- 深度分析模板样式: {path} ---")
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active # 假设第一个分页就是 D&I 模板
    
    # 检查前 25 行的关键单元格
    for row in range(1, 25):
        row_data = []
        for col in range(1, 10):
            cell = ws.cell(row=row, column=col)
            val = cell.value
            color = cell.fill.start_color.index if cell.fill else "None"
            font_bold = cell.font.bold if cell.font else False
            row_data.append(f"[{val} (C:{color}, B:{font_bold})]")
        print(f"Row {row:2}: {' '.join(row_data)}")

if __name__ == "__main__":
    path = r"C:\Users\Laptop\Downloads\【2026】ITAC_P2P_02 采购收货入应付暂估会计凭证.xlsx"
    analyze_template_style(path)
