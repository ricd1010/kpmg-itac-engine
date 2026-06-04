
import openpyxl

path = r'C:\Users\Laptop\Downloads\【2026】ITAC_P2P_02 采购收货入应付暂估会计凭证.xlsx'

try:
    wb = openpyxl.load_workbook(path, data_only=True)
    sheet = wb.worksheets[0]
    
    keywords = ["Entity", "System", "被审计单位", "系统名称", "审计期间", "Client"]
    
    for r in range(1, 100):
        for c in range(1, 20):
            val = sheet.cell(row=r, column=c).value
            if val and isinstance(val, str):
                for kw in keywords:
                    if kw in val:
                        print(f"Found '{kw}' at R{r}C{c}: {val}")

except Exception as e:
    print(f"Error: {e}")
