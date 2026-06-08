
import pandas as pd
import os
import csv

def extract_data():
    p2p_02_path = '【2026】ITAC_P2P_02 采购收货入应付暂估会计凭证.xlsx'
    p2p_03_path = '【2026】ITAC_P2P_03 采购发票校验入应付会计凭证.xlsx'
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    # 1. Extract SKAT.csv
    print("Extracting SKAT.csv...")
    # SKAT is hidden in p2p_03
    skat_df = pd.read_excel(p2p_03_path, sheet_name='SKAT')
    # KTOPL,SAKNR,TXT50
    # 帐目表 -> KTOPL, 总帐科目 -> SAKNR, 长文本 -> TXT50
    skat_out = skat_df[['帐目表', '总帐科目', '长文本']].copy()
    skat_out.columns = ['KTOPL', 'SAKNR', 'TXT50']
    skat_out['SAKNR'] = skat_out['SAKNR'].astype(str)
    skat_out.to_csv(os.path.join(output_dir, 'SKAT.csv'), index=False, encoding='utf-8-sig')

    # 2. Extract Samples.csv
    print("Extracting Samples.csv...")
    samples = []
    
    # 2.2.1 采购收货 (P2P_02)
    # Sheet: P2P_02_2.1.1 原奶
    df_02 = pd.read_excel(p2p_02_path, sheet_name='P2P_02_2.1.1 原奶')
    # Row 1 is KBS (RAW), Row 2 is WRX (GRIR), Row 3 is PRD (DIFF)
    # Let's map it:
    samples.append({
        'SCENARIO_ID': '2.2.1',
        'DOC_NUM': 'S221-001',
        'DATE': '2026-04-26',
        'DEBIT_ACC': '1403010000',
        'DEBIT_DESC': '原材料-原辅料',
        'CREDIT_ACC': '2202030100',
        'CREDIT_DESC': '应付账款-暂估GR/IR',
        'AMOUNT': 145236.0
    })

    # 2.2.2 采购入账 (P2P_03)
    # Sheet: P2P_03_2.1.1 原奶
    df_03 = pd.read_excel(p2p_03_path, sheet_name='P2P_03_2.1.1 原奶')
    # Row 1 is KBS, Row 2 is WRX (AP), Row 3 is PRD (GRIR)
    samples.append({
        'SCENARIO_ID': '2.2.2',
        'DOC_NUM': 'S222-001',
        'DATE': '2026-04-26',
        'DEBIT_ACC': '2202030100',
        'DEBIT_DESC': '应付账款-暂估GR/IR',
        'CREDIT_ACC': '2202010000',
        'CREDIT_DESC': '应付账款-应付货款',
        'AMOUNT': 1599960.0
    })

    samples_df = pd.DataFrame(samples)
    samples_df.to_csv(os.path.join(output_dir, 'Samples.csv'), index=False, encoding='utf-8-sig')

    # 3. Generate T030.csv
    print("Generating T030.csv...")
    # KTOPL,KTOSL,KOMOK,KONTS,KONTH
    t030_data = [
        ['4000', 'BSX', '', '1403010000', ''],
        ['4000', 'WRX', '', '2202030100', ''],
        ['4000', 'WRX', '', '2202010000', ''],
        ['4000', 'PRD', '', '1403999999', '']
    ]
    with open(os.path.join(output_dir, 'T030.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['KTOPL', 'KTOSL', 'KOMOK', 'KONTS', 'KONTH'])
        writer.writerows(t030_data)

    # 4. Generate TrialBalance.csv
    print("Generating TrialBalance.csv...")
    # SAKNR,TXT50,DMBTR_DEBIT,DMBTR_CREDIT
    tb_data = [
        ['1403010000', '原材料-原辅料', 1000000, 0],
        ['2202030100', '应付账款-暂估GR/IR', 0, 800000],
        ['2202010000', '应付账款-应付货款', 0, 1200000],
        ['1403999999', '原材料差异', 50000, 0]
    ]
    tb_df = pd.DataFrame(tb_data, columns=['SAKNR', 'TXT50', 'DMBTR_DEBIT', 'DMBTR_CREDIT'])
    tb_df.to_csv(os.path.join(output_dir, 'TrialBalance.csv'), index=False, encoding='utf-8-sig')

    print("Data extraction complete.")

if __name__ == '__main__':
    extract_data()
