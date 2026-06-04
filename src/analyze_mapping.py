import os
import sys
import pandas as pd
import io

# Add current dir to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_validator import DataValidator
from scenario_mapper import AccountMapper

class SF(io.BytesIO):
    def __init__(self, b, n): super().__init__(b); self.name = n

def analyze():
    base_dir = r"data/新希望测试数据"
    skat_path = os.path.join(base_dir, "SKAT.xls")
    t030_path = os.path.join(base_dir, "T030 HEBING.xlsx")
    
    print("=== 审计场景识别诊断报告 ===")
    
    # 1. 尝试读取 SKAT 和 Trial Balance
    print(f"\n[Step 1] 读取各表格获取科目信息...")
    all_accounts_with_desc = {} # {saknr: desc}

    def collect_from_file(path, f_type):
        with open(path, 'rb') as f: fb = f.read()
        is_v, msg, df = DataValidator.validate_file(SF(fb, os.path.basename(path)), f_type)
        if is_v:
            # Try to find SAKNR and TXT50 (or their mapped versions)
            s_col = "SAKNR" if "SAKNR" in df.columns else None
            t_col = "TXT50" if "TXT50" in df.columns else None
            if s_col and t_col:
                for _, row in df.iterrows():
                    all_accounts_with_desc[str(row[s_col])] = str(row[t_col])
            print(f"✅ 从 {os.path.basename(path)} 收集了数据")

    collect_from_file(skat_path, "SKAT")
    collect_from_file(os.path.join(base_dir, "课余表-牧业生产.xls"), "TrialBalance")
    collect_from_file(os.path.join(base_dir, "课余表—乳业销售.xls"), "TrialBalance")

    print(f"💡 总共收集到 {len(all_accounts_with_desc)} 个唯一科目描述")

    # 2. 检查分类关键字匹配
    print("\n[Step 2] 检查科目分类关键字匹配...")
    mapper = AccountMapper(None)
    keywords = mapper.role_keywords
    found_roles = {}
    
    for saknr, txt50 in all_accounts_with_desc.items():
        for role, kws in keywords.items():
            if any(kw in txt50 for kw in kws):
                found_roles[role] = found_roles.get(role, 0) + 1
    
    if not found_roles:
        print("❌ 警告: 依然没有科目匹配到关键字！")
        print(f"   随机科目示例: {list(all_accounts_with_desc.values())[:10]}")
    else:
        print(f"✅ 关键字匹配结果: {found_roles}")

    # 3. 尝试读取 T030
    print(f"\n[Step 3] 读取 T030 (配置表)...")
    with open(t030_path, 'rb') as f:
        fb = f.read()
    is_v, msg, df_t030 = DataValidator.validate_file(SF(fb, "T030 HEBING.xlsx"), "T030")
    if not is_v:
        print(f"❌ T030 解析失败: {msg}")
        return
    print(f"✅ T030 解析成功，共有 {len(df_t030)} 条自动过账配置")
    
    # 4. 检查 T030 科目是否存在于收集到的科目集中
    print("\n[Step 4] 检查 T030 与 收集到的科目描述 的交集...")
    t030_accounts = set(df_t030['KONTS'].unique()).union(set(df_t030['KONTH'].unique()))
    collected_accounts = set(all_accounts_with_desc.keys())
    intersection = t030_accounts.intersection(collected_accounts)
    print(f"   T030 中涉及科目总数: {len(t030_accounts)}")
    print(f"   收集到的科目总数: {len(collected_accounts)}")
    print(f"   交集科目数: {len(intersection)}")
    
    if intersection:
        print(f"✅ 交集示例: {list(intersection)[:5]}")
        # Show matching for a few intersection accounts
        print("\n[示例匹配详情]:")
        for acc in list(intersection)[:5]:
            desc = all_accounts_with_desc[acc]
            roles = []
            for role, kws in keywords.items():
                if any(kw in desc for kw in kws): roles.append(role)
            print(f"   科目 {acc} ({desc}) -> 识别角色: {roles}")
    else:
        print("❌ 严重错误: T030 中的科目在收集到的描述表里一个都找不到！")
    
    print("\n=== 诊断结束 ===")

if __name__ == "__main__":
    analyze()
