import pandas as pd
import io
import re
import os

class DataValidator:
    REQUIRED_COLUMNS = {
        "SKAT": ["SAKNR", "TXT50"],
        "T030": ["KONTS", "KONTH"], 
        "TrialBalance": ["SAKNR", "DMBTR_DEBIT", "DMBTR_CREDIT"],
        "Samples": ["DOC_NUM", "SAKNR", "AMOUNT"]
    }

    @staticmethod
    def validate_file(file_obj, file_type):
        error_log = []
        df = None
        try:
            file_obj.seek(0)
            raw_content = file_obj.read()
            
            # --- 阶段 1：Excel ---
            for eng in ['openpyxl', 'xlrd']:
                try:
                    df_raw = pd.read_excel(io.BytesIO(raw_content), header=None, engine=eng)
                    df = DataValidator._find_real_header(df_raw, file_type)
                    if df is not None: break
                except Exception as e:
                    error_log.append(f"Excel({eng})失败")

            # --- 阶段 2：文本拆解 ---
            if df is None:
                for enc in ['utf-16', 'utf-8-sig', 'gb18030', 'latin1']:
                    try:
                        text = raw_content.decode(enc)
                        lines = [l for l in text.splitlines() if l.strip()]
                        split_data = []
                        for line in lines:
                            parts = [p.strip() for p in re.split(r'\t+|\s{2,}', line) if p.strip()]
                            if parts: split_data.append(parts)
                        if split_data:
                            max_cols = max(len(r) for r in split_data)
                            normalized_data = [r + [None]*(max_cols-len(r)) for r in split_data]
                            df_raw = pd.DataFrame(normalized_data)
                            df = DataValidator._find_real_header(df_raw, file_type)
                            if df is not None: break
                    except: continue

            # --- 阶段 3：HTML ---
            if df is None:
                try:
                    df_raw = pd.read_html(io.BytesIO(raw_content))[0]
                    df = DataValidator._find_real_header(df_raw, file_type)
                except: pass

            if df is None:
                return False, "无法读取文件，格式识别失败。", None

            # --- 阶段 4：列名映射 ---
            df.columns = [str(c).strip() for c in df.columns]
            df = DataValidator._map_columns(df, file_type)
            
            # T030 专项补丁
            if file_type == "T030":
                if "KONTS" not in df.columns and "SAKNR" in df.columns:
                    df = df.rename(columns={"SAKNR": "KONTS"})
                if "KONTH" not in df.columns:
                    pos = [c for c in df.columns if ".1" in str(c) or "Unnamed" in str(c) or "科目" in str(c)]
                    if len(pos) > 0:
                        for p in pos:
                            if p != "KONTS": df = df.rename(columns={p: "KONTH"}); break
                    if "KONTH" not in df.columns and "KONTS" in df.columns: df["KONTH"] = df["KONTS"]

            required = DataValidator.REQUIRED_COLUMNS.get(file_type, [])
            missing = [col for col in required if col not in df.columns]
            
            # TrialBalance 特殊保底
            if missing and file_type == "TrialBalance" and df.shape[1] >= 5:
                df = DataValidator._positional_fallback(df)
                missing = [col for col in required if col not in df.columns]

            if missing:
                return False, f"表缺失必要字段: {', '.join(missing)}。检测到列: {df.columns.tolist()}", None

            # --- 阶段 5：物理列清洗 (防重名) ---
            new_col_names = []
            counts = {}
            for c in df.columns:
                c_str = str(c)
                if c_str in counts:
                    counts[c_str] += 1
                    new_col_names.append(f"{c_str}_{counts[c_str]}")
                else:
                    counts[c_str] = 0
                    new_col_names.append(c_str)
            df.columns = new_col_names

            for i in range(df.shape[1]):
                col_name = df.columns[i]
                if any(k in col_name for k in ["SAKNR", "DOC_NUM", "KONTS", "KONTH", "DEBIT_ACC", "CREDIT_ACC"]):
                    df.iloc[:, i] = df.iloc[:, i].astype(str).str.strip().str.replace('\.0$', '', regex=True)
                if any(k in col_name for k in ["DMBTR_DEBIT", "DMBTR_CREDIT", "AMOUNT"]):
                    s = df.iloc[:, i].astype(str).str.replace('[^0-9\.\-]', '', regex=True)
                    df.iloc[:, i] = pd.to_numeric(s, errors='coerce').fillna(0.0)

            return True, "验证通过", df
        except Exception as e:
            return False, f"验证器异常: {str(e)}", None

    @staticmethod
    def _find_real_header(df_raw, file_type):
        """寻找表头行：智能计分算法"""
        KEYWORDS = {
            "saknr": 20, "konts": 20, "konth": 20, "总帐科目": 20, "总账科目": 20,
            "dmbtr": 15, "借方余额": 15, "贷方余额": 15, "借方金额": 15, "贷方金额": 15,
            "评估分组代码": 15, "科目修改": 15, "trs": 15, "valcl": 15,
            "已结转余额": 15, "前一期间的余额": 15, "在制表期间的借方余额": 15,
            "txt50": 10, "短文本": 10, "科目名称": 10, "科目描述": 10, "帐目表": 10
        }
        # 严禁词：只针对纯粹的 metadata 标题
        FORBIDDEN = ["时间", "制表", "筛选", "页码", "1/"]

        best_idx = -1
        max_score = -99
        
        for i, row in df_raw.head(50).iterrows():
            vals = [str(v).strip().lower() for v in row.values if pd.notna(v) and str(v).strip()]
            if len(vals) < 2: continue
            
            row_str = " ".join(vals)
            score = 0
            
            # 1. 禁词检查
            for fk in FORBIDDEN:
                if fk in row_str: score -= 50
            
            # 2. 关键词匹配
            for k, w in KEYWORDS.items():
                if k in row_str: score += w
            
            # 3. 结构特征：真实表头通常不含纯数字
            num_count = sum(1 for v in vals if re.match(r'^-?\d+(\.\d+)?$', v.replace(',', '')))
            if num_count > len(vals) * 0.5:
                score -= 40 # 数据行大幅扣分
            
            # 4. 列数奖励
            if len(vals) >= 6: score += 10
            
            if score > max_score:
                max_score = score
                best_idx = i
        
        if max_score >= 10:
            row = df_raw.iloc[best_idx]
            new_cols = []
            for j, val in enumerate(row.values):
                v = str(val).strip()
                new_cols.append(v if (v and v != 'nan') else f"Col_{j}")
            res = df_raw.iloc[best_idx+1:].copy()
            res.columns = new_cols
            return res.dropna(how='all')
        return None

    @staticmethod
    def _positional_fallback(df):
        new_map = {}
        for i in range(df.shape[1]):
            col_data = df.iloc[:, i].astype(str).head(100)
            if "SAKNR" not in new_map.values() and col_data.str.match(r'^\d{8,10}$').sum() > 20:
                new_map[df.columns[i]] = "SAKNR"
            elif col_data.str.contains(r'\.').sum() > 20:
                nums = pd.to_numeric(col_data.str.replace(',', ''), errors='coerce')
                if nums.notna().sum() > 30:
                    if "DMBTR_DEBIT" not in new_map.values(): new_map[df.columns[i]] = "DMBTR_DEBIT"
                    elif "DMBTR_CREDIT" not in new_map.values(): new_map[df.columns[i]] = "DMBTR_CREDIT"
        return df.rename(columns=new_map)

    @staticmethod
    def _map_columns(df, file_type):
        MAPPING = {
            "KONTS": ["konts", "借方科目", "总帐科目", "总账科目"],
            "KONTH": ["konth", "贷方科目", "总帐科目", "总账科目"],
            "SAKNR": ["saknr", "科目", "总账科目", "总帐科目", "G/L Account"],
            "TXT50": ["txt50", "科目描述", "科目名称", "短文本", "总分类帐名称"],
            "DMBTR_DEBIT": ["dmbtr_debit", "借方金额", "在制表期间的借方余额", "已结转余额", "借方", "前一期间的余额"],
            "DMBTR_CREDIT": ["dmbtr_credit", "贷方金额", "报表期间的贷方余额", "累计余额", "贷方"],
            "DOC_NUM": ["doc_num", "凭证号", "会计凭证"],
            "DATE": ["date", "日期", "过账日期"],
            "AMOUNT": ["amount", "金额", "交易金额"],
            "SHKZG": ["shkzg", "借/贷标识", "S/H"],
            "KTOSL": ["ktosl", "事务", "交易变式", "事务码", "TRS"],
            "KOMOK": ["komok", "科目修改", "修改码"]
        }
        final_names = {}
        used_indices = set()
        for target, aliases in MAPPING.items():
            found = False
            for alias in aliases:
                for idx, actual in enumerate(df.columns):
                    if idx in used_indices: continue
                    a_str = str(actual).lower()
                    al_str = alias.lower()
                    if al_str == a_str or al_str in a_str:
                        final_names[actual] = target
                        used_indices.add(idx)
                        found = True; break
                if found: break
        return df.rename(columns=final_names)

    @staticmethod
    def validate_audit_context(entity_name, system_name, start_date, end_date):
        if not entity_name or len(entity_name.strip()) < 2: return False, "单位名称无效"
        return True, "验证通过"
