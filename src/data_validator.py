import pandas as pd
import io
import re

class DataValidator:
    REQUIRED_COLUMNS = {
        "SKAT": ["SAKNR", "TXT50"],
        "T030": ["KONTS", "KONTH"], 
        "TrialBalance": ["SAKNR", "DMBTR_DEBIT", "DMBTR_CREDIT"],
        "Samples": ["DOC_NUM", "SAKNR", "AMOUNT"] # Minimum for raw line items
    }

    @staticmethod
    def validate_file(file_obj, file_type):
        """
        Validates the uploaded CSV or XLSX file for the specified type.
        Returns (is_valid, message, cleaned_df)
        """
        try:
            filename = file_obj.name.lower()
            
            HEADER_KEYWORDS = {
                "saknr": 2, "txt50": 2, "konts": 2, "konth": 2, "总帐科目": 2, "总账科目": 2,
                "借方余额": 2, "贷方余额": 2, "借方金额": 2, "贷方金额": 2,
                "科目": 1, "帐": 1, "账": 1, "account": 1, "doc": 1, "amount": 1, "金额": 1,
                "余额": 1, "借方": 1, "贷方": 1, "公司": 1, "文本": 1, "描述": 1
            }
            FORBIDDEN_HEADER_KEYWORDS = ["时间", "页", "日期", "制表", "筛选", "青岛", "四川", "新希望"]

            def find_real_header(df_raw):
                """Scans top rows to find the row that most looks like a header"""
                best_row_idx = -1
                max_score = -999
                
                for i, row in df_raw.head(100).iterrows():
                    vals = [str(v).strip().lower() for v in row.values if pd.notna(v) and str(v).strip()]
                    if not vals: continue 
                    
                    row_str = " ".join(vals)
                    score = 0
                    
                    if any(k in row_str for k in FORBIDDEN_HEADER_KEYWORDS):
                        score -= 5
                    
                    for k, weight in HEADER_KEYWORDS.items():
                        if k in row_str: score += weight
                    
                    if len(vals) >= 5: score += 1
                    
                    if score > max_score:
                        max_score = score
                        best_row_idx = i
                
                if max_score >= 3:
                    row = df_raw.iloc[best_row_idx]
                    raw_cols = [str(c).strip() for c in row.values]
                    new_cols = []
                    counts = {}
                    for c in raw_cols:
                        if not c or c == 'nan' or c == 'None': c = f"Unnamed_{len(new_cols)}"
                        if c in counts:
                            counts[c] += 1
                            new_cols.append(f"{c}.{counts[c]}")
                        else:
                            counts[c] = 0
                            new_cols.append(c)

                    df_adjusted = df_raw.iloc[best_row_idx+1:].copy()
                    df_adjusted.columns = new_cols
                    return df_adjusted.dropna(how='all')
                return df_raw

            # --- Reading Logic with "Fake" Excel support ---
            df = None
            if filename.endswith('.csv'):
                content = file_obj.getvalue().decode('utf-8-sig')
                df = pd.read_csv(io.StringIO(content))
                df = find_real_header(df)
            elif filename.endswith('.xlsx') or filename.endswith('.xls'):
                try:
                    # 1. Try standard Excel
                    df_raw = pd.read_excel(file_obj, header=None)
                    df = find_real_header(df_raw)
                except:
                    # 2. Try Manual UTF-16 Multi-Split (The "Universal SAP Opener")
                    try:
                        file_obj.seek(0)
                        raw_bytes = file_obj.read()
                        text = raw_bytes.decode('utf-16')
                        lines = [l.strip() for l in text.split('\n') if l.strip()]
                        
                        split_data = []
                        for l in lines:
                            if '\t' in l:
                                parts = [p.strip() for p in re.split(r'\t+', l) if p.strip()]
                            else:
                                parts = [p.strip() for p in re.split(r'\s{2,}', l) if p.strip()]
                            if parts: split_data.append(parts)
                        
                        if split_data:
                            df_raw = pd.DataFrame(split_data)
                            df = find_real_header(df_raw)
                    except:
                        file_obj.seek(0)
                        try:
                            df_raw = pd.read_html(file_obj)[0]
                            df = find_real_header(df_raw)
                        except:
                            file_obj.seek(0)
                            df_raw = pd.read_csv(file_obj, header=None, on_bad_lines='skip')
                            df = find_real_header(df_raw)

            if df is None:
                return False, "文件读取失败，格式无法识别", None
            
            # --- Standard Validation & Mapping ---
            df = DataValidator._map_columns(df, file_type)
            detected_cols = [str(c) for c in df.columns]

            required = DataValidator.REQUIRED_COLUMNS.get(file_type, [])
            missing = [col for col in required if col not in df.columns]
            
            if file_type == "T030":
                if "KONTS" not in df.columns and "KONTH" not in df.columns:
                    return False, f"T030 表识别失败。未找到科目列。检测到列名: {detected_cols}", None
            elif missing:
                return False, f"{file_type} 表缺失必要字段: {', '.join(missing)}。检测到列名: {detected_cols}", None

            # Basic Cleaning
            df = df.dropna(how='all')
            for col in ["SAKNR", "DEBIT_ACC", "CREDIT_ACC", "DOC_NUM", "KONTS", "KONTH"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip().str.replace('\.0$', '', regex=True)
            for col in ["DMBTR_DEBIT", "DMBTR_CREDIT", "AMOUNT"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace('[^0-9\.\-]', '', regex=True)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            if df.empty:
                return False, f"{file_type} 表为空，请检查数据内容", None

            return True, "验证通过", df
        except Exception as e:
            return False, f"系统级异常: {str(e)}", None

    @staticmethod
    def _map_columns(df, file_type):
        MAPPING = {
            "KONTS": ["konts", "借方科目", "Debit Account", "DEBIT_ACC", "总帐科目", "总账科目"],
            "KONTH": ["konth", "贷方科目", "Credit Account", "CREDIT_ACC", "总帐科目.1", "总账科目.1"],
            "SAKNR": ["saknr", "科目", "总账科目", "总帐科目", "G/L Account", "Account", "Account Number", "总账科目"],
            "TXT50": ["txt50", "科目描述", "科目名称", "Description", "Account Name", "短文本", "总分类帐名称"],
            "DMBTR_DEBIT": ["dmbtr_debit", "借方金额", "Debit Amount", "Balance Debit", "前一期间的余额", "在制表期间的借方余额"],
            "DMBTR_CREDIT": ["dmbtr_credit", "贷方金额", "Credit Amount", "Balance Credit", "累计余额", "报表期间的贷方余额"],
            "DOC_NUM": ["doc_num", "凭证号", "会计凭证", "Document Number", "Voucher", "开票凭证"],
            "DATE": ["date", "日期", "过账日期", "Posting Date", "Posting_Date"],
            "AMOUNT": ["amount", "金额", "交易金额", "Value", "Total Amount"],
            "SHKZG": ["shkzg", "借/贷标识", "借贷标识", "D/C Indicator", "S/H"]
        }

        priority_order = ["SAKNR", "TXT50", "DMBTR_DEBIT", "DMBTR_CREDIT", "DOC_NUM", "DATE", "AMOUNT", "SHKZG"]
        if file_type == "T030":
            priority_order = ["KONTS", "KONTH"] + priority_order
        else:
            priority_order += ["KONTS", "KONTH"]

        current_cols = {str(c).lower().strip(): c for c in df.columns}
        new_names = {}
        used_source_cols = set()

        for internal_name in priority_order:
            if internal_name in MAPPING:
                candidates = MAPPING[internal_name]
                for cand in candidates:
                    cand_lower = cand.lower().strip()
                    if cand_lower in current_cols:
                        source_col = current_cols[cand_lower]
                        if source_col not in used_source_cols:
                            new_names[source_col] = internal_name
                            used_source_cols.add(source_col)
                            break 
        return df.rename(columns=new_names)

    @staticmethod
    def validate_audit_context(entity_name, system_name, start_date, end_date):
        if not entity_name or len(entity_name.strip()) < 2:
            return False, "被审计单位名称无效"
        if not system_name or len(system_name.strip()) < 2:
            return False, "系统名称无效"
        if start_date >= end_date:
            return False, "开始日期必须早于结束日期"
        return True, "验证通过"
