import streamlit as st
import pandas as pd
import os
import datetime
import re
import base64
import time
import uuid
from core1_main import Core1Orchestrator
from core2_main import Core2Orchestrator
from report_generator import ReportGenerator
from data_validator import DataValidator
from dotenv import load_dotenv

load_dotenv()
DEFAULT_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# KPMG Heritage Branding Colors
KPMG_BLUE = "#00338D"
KPMG_TEAL = "#00A3A1"
KPMG_DARK_GREY = "#1A1A1A"
KPMG_LIGHT_GREY = "#F7F9FC"

# Generate custom KPMG Favicon
fav_svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
    <rect width="100" height="100" fill="{KPMG_BLUE}"/>
    <text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" font-family="Arial, sans-serif" font-weight="bold" font-size="70" fill="white">AC</text>
</svg>
"""
fav_b64 = base64.b64encode(fav_svg.encode()).decode()

st.set_page_config(
    page_title="KPMG ITAC Auto-Workpaper Engine",
    page_icon=f"data:image/svg+xml;base64,{fav_b64}",
    layout="wide",
)

# --- CACHING ENGINES ---
@st.cache_resource
def get_ocr_engine():
    from ocr_processor import OCRProcessor
    return OCRProcessor()

# Custom KPMG Styling - Forced Professional Contrast (Dark Mode Compatibility)
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap');
    
    html, body, [class*="css"], .stApp {{
        font-family: 'Open Sans', sans-serif !important;
        font-size: 16px !important;
        color: {KPMG_DARK_GREY} !important;
        background-color: {KPMG_LIGHT_GREY} !important;
    }}
    
    /* Force Full Screen Width and Remove Margins */
    .main .block-container {{
        max-width: 100vw !important;
        padding: 0px !important;
        margin: 0px !important;
        width: 100vw !important;
    }}
    
    [data-testid="stAppViewBlockContainer"] {{
        max-width: 100vw !important;
        padding: 0px !important;
        margin: 0px !important;
        width: 100vw !important;
    }}

    [data-testid="stHeader"] {{
        display: none !important;
    }}
    
    footer {{
        display: none !important;
    }}

    /* Remove top padding for the first element */
    [data-testid="stAppViewContainer"] {{
        padding: 0px !important;
    }}

    
    [data-testid="stSidebar"] {{
        background-color: {KPMG_BLUE} !important;
        padding-top: 0.1rem !important;
    }}
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stText, [data-testid="stSidebar"] p {{
        color: white !important;
        font-size: 15px !important;
        font-weight: 600 !important;
    }}
    
    .logo-container {{
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        margin-bottom: 0.5rem;
        margin-top: 0.5rem;
    }}
    .massive-logo {{
        width: 320px !important;
        display: block;
        margin: 0 auto;
    }}

    .audit-card {{
        background-color: white !important;
        padding: 2.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-top: 6px solid {KPMG_BLUE};
        margin-bottom: 2rem;
        color: {KPMG_DARK_GREY} !important;
    }}
    
    .stButton>button {{
        background-color: {KPMG_BLUE} !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.8rem 2.5rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        transition: all 0.3s ease !important;
        display: block;
        margin-left: auto !important;
        margin-right: auto !important;
        min-height: 3.4rem !important;
    }}
    .stButton>button:hover {{ 
        background-color: {KPMG_TEAL} !important; 
        box-shadow: 0 4px 15px rgba(0,51,141,0.3) !important;
    }}
    
    h1 {{ color: {KPMG_BLUE} !important; font-size: 38px !important; font-weight: 800 !important; margin-bottom: 0px !important;}}
    .sub-caption {{ color: {KPMG_DARK_GREY} !important; font-size: 22px; font-weight: 500; margin-top: 5px !important; }}
    h2, h3 {{ color: {KPMG_BLUE} !important; font-size: 26px !important; font-weight: 700 !important; border-bottom: 2px solid {KPMG_TEAL}; padding-bottom: 12px; }}
    
    label p {{ color: {KPMG_DARK_GREY} !important; font-weight: 600 !important; }}
    
    .sidebar-footer {{
        position: fixed;
        bottom: 25px;
        left: 20px;
        color: rgba(255,255,255,0.8) !important;
        font-size: 14px !important;
        font-weight: 400 !important;
    }}
    
    .stAlert {{ background-color: white !important; color: {KPMG_DARK_GREY} !important; }}

    /* Universal Centering for Spinner and Status Text */
    [data-testid="stSpinner"], [data-testid="stStatusWidget"] {{
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
        margin-top: 1.5rem !important;
        margin-bottom: 1.5rem !important;
        text-align: center !important;
    }}
    [data-testid="stSpinner"] > div, [data-testid="stStatusWidget"] > div {{
        width: auto !important;
        text-align: center !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        color: {KPMG_BLUE} !important;
    }}

    /* Vertical Centering for Toolbar Elements */
    [data-testid="column"] {{
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }}
    
    .stSelectbox {{
        margin-top: -15px !important; /* Counter-act default label space even when collapsed */
    }}
    </style>
    """, unsafe_allow_html=True)

# Helper for logo
def get_base64_image(image_path):
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as f: data = f.read()
            return base64.b64encode(data).decode()
    except: pass
    return None

# --- SESSION INITIALIZATION ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "current_step" not in st.session_state: st.session_state.current_step = 1
if "audit_context" not in st.session_state: st.session_state.audit_context = {}
if "ocr_samples" not in st.session_state: st.session_state.ocr_samples = []
if "processed_image_names" not in st.session_state: st.session_state.processed_image_names = set()
if "results" not in st.session_state: st.session_state.results = None
if "api_key_valid" not in st.session_state: st.session_state.api_key_valid = False
if "api_check_done" not in st.session_state: st.session_state.api_check_done = False
if "show_balloons" not in st.session_state: st.session_state.show_balloons = False
if "ocr_busy" not in st.session_state: st.session_state.ocr_busy = False

# Background API Validation
if not st.session_state.api_check_done:
    if DEFAULT_KEY:
        from llm_client import LLMClient
        temp_client = LLMClient(api_key=DEFAULT_KEY)
        is_ok, msg = temp_client.validate_api_key()
        st.session_state.api_key_valid = is_ok
        st.session_state.api_check_done = True
        if is_ok: 
            st.toast("🚀 KPMG AI Engine: DeepSeek API 已成功接入", icon="✅")
        else: 
            st.error(f"❌ AI 引擎校验失败 (Key: {DEFAULT_KEY[:6]}...): {msg}")
    else:
        st.session_state.api_key_valid = False
        st.session_state.api_check_done = True
        st.info("ℹ️ 系统正处于 Mock Mode (未检测到内置 API Key)")

# Isolated Data Directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_DATA_DIR = os.path.join(BASE_DIR, "data", "sessions", st.session_state.session_id)
if not os.path.exists(SESSION_DATA_DIR):
    os.makedirs(SESSION_DATA_DIR, exist_ok=True)

# Main Header Area with Logo
logo_path = os.path.join(os.path.dirname(__file__), "kpmg_logo_official_white.png")
# Note: Since sidebar is removed, we'll use a blue header bar or just the logo
logo_b64 = get_base64_image(logo_path)

header_html = f"""
<div style="background-color: {KPMG_BLUE}; padding: 3rem 4rem; border-radius: 16px; margin: 1rem 1rem 2rem 1rem; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 8px 24px rgba(0,51,141,0.2);">
    <div style="display: flex; align-items: center;">
        <img src="data:image/png;base64,{logo_b64}" style="height: 65px; margin-right: 35px;">
        <div style="color: white; display: flex; flex-direction: column; justify-content: center;">
            <span style="color: #FFFFFF !important; font-size: 42px !important; font-weight: 800; display: block; margin-bottom: 2px; line-height: 1.1;">ITAC 自动化底稿生成中心</span>
            <p style="margin: 0 !important; font-size: 17px; opacity: 0.85; color: #FFFFFF !important; font-weight: 500;">专业的 SAP 系统自动化控制测试辅助平台 | 毕马威审计技术部</p>
        </div>
    </div>
    <div style="text-align: right; color: white;">
        <div style="font-size: 14px; font-weight: 600; letter-spacing: 1px;">SYSTEM ONLINE</div>
        <div style="font-size: 11px; opacity: 0.7; margin-top: 4px;">Session Tracking: {st.session_state.session_id[:12].upper()}</div>
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# Model & Status Bar
c1, c2 = st.columns([3, 1])
with c1:
    if st.session_state.api_key_valid:
        st.success("🤖 已成功部署DeepSeek API")
    else:
        st.warning("⚠️ 基础分析模式 (Mock Mode)")
with c2:
    selected_model = st.selectbox("分析模型", ["deepseek-chat", "deepseek-reasoner"], label_visibility="collapsed")

st.divider()

# --- MAIN RENDER LOGIC ---
if st.session_state.results:
    if st.session_state.show_balloons:
        st.balloons(); st.session_state.show_balloons = False
    res = st.session_state.results
    t1, t2, t3 = st.tabs(["📊 1. 场景分析总览", "📝 2. AI 穿行测试叙述", "📥 3. 底稿成果下载"])
    with t1:
        st.subheader("识别场景与重要性排序")
        if res["ranked"]:
            df_ranked = pd.DataFrame(res["ranked"])
            df_ranked["accounts_display"] = df_ranked["accounts"].apply(lambda x: "\n".join(x))
            st.dataframe(df_ranked[["name", "total_value", "accounts_display"]].rename(columns={"name": "审计场景", "total_value": "涉及金额", "accounts_display": "关联科目"}), use_container_width=True)
    with t2:
        st.subheader("TOD/TOE 穿行测试描述")
        for it in res["di"]:
            with st.expander(f"📌 {it['scenario']}"):
                st.info(it["di_description"]); st.write("**样本细节记录 (TOE):**"); st.json(it["sample_table"])
    with t3:
        st.subheader("最终成果文件导出")
        with open(res["report_path"], "rb") as f:
            st.download_button(label="📥 下载最终 Excel 审计底稿", data=f.read(), file_name=f"ITAC_WP_{st.session_state.audit_context.get('entity_name','Audit')}.xlsx", use_container_width=True)
        st.write("") 
        if st.button("🔄 开启新的审计任务", use_container_width=True):
            st.session_state.current_step = 1; st.session_state.results = None; st.session_state.ocr_samples = []; st.session_state.processed_image_names = set(); st.session_state.show_balloons = False; st.rerun()
        st.write("---"); st.caption("© 2026 KPMG. All rights reserved. | IT Audit Technology & Innovation")
    st.stop()

# Progress
steps = ["📌 审计背景", "📊 基础清单", "📸 样本采集"]
st.write(f"当前进度: **第 {st.session_state.current_step} 步 / 共 3 步** — {steps[st.session_state.current_step-1]}")
st.progress(st.session_state.current_step / 3.0)

# --- STEP 1 ---
if st.session_state.current_step == 1:
    st.subheader("步骤 1: 设置审计背景信息")
    with st.form("step1_form"):
        c1, c2 = st.columns(2)
        with c1:
            entity_name = st.text_input("被审计单位", placeholder="输入公司名称")
            system_name = st.text_input("测试系统/版本", value="SAP S/4HANA v2023")
        with c2:
            period_start = st.date_input("审计起始日期", value=datetime.date(2025, 1, 1))
            period_end = st.date_input("审计截止日期", value=datetime.date(2025, 12, 31))
        st.write("")
        col_btn = st.columns([1, 1.5, 1])
        with col_btn[1]:
            if st.form_submit_button("下一步：上传清单", use_container_width=True):
                if entity_name and system_name:
                    st.session_state.audit_context = {"entity_name": entity_name, "system_name": system_name, "period_start": str(period_start), "period_end": str(period_end)}
                    st.session_state.current_step = 2; st.rerun()
                else: st.error("❗ 请完整填写背景信息。")

# --- STEP 2 ---
elif st.session_state.current_step == 2:
    st.subheader("步骤 2: 上传基础数据表 (T030, SKAT, 余额表)")
    u1, u2, u3 = st.columns(3)
    with u1: t030_file = st.file_uploader("T030 配置表", type=["csv", "xlsx", "xls"])
    with u2: skat_file = st.file_uploader("SKAT 科目表", type=["csv", "xlsx", "xls"])
    with u3: tb_file = st.file_uploader("余额表", type=["csv", "xlsx", "xls"])
    st.write("---")
    nav_cols = st.columns([1, 1.5, 1.5, 1])
    with nav_cols[1]:
        if st.button("返回上一步", use_container_width=True): st.session_state.current_step = 1; st.rerun()
    with nav_cols[2]:
        if st.button("确认并下一步", use_container_width=True):
            if t030_file and skat_file and tb_file:
                with st.spinner("数据校验中..."):
                    all_v = True
                    for f_t, f_o in {"T030": t030_file, "SKAT": skat_file, "TrialBalance": tb_file}.items():
                        is_v, msg, df = DataValidator.validate_file(f_o, f_t)
                        if not is_v: st.error(f"❌ {f_t} 失败: {msg}"); all_v = False; break
                        # Force isolated output path
                        df.to_csv(os.path.join(SESSION_DATA_DIR, f"{f_t}.csv"), index=False, encoding='utf-8-sig')
                    if all_v: st.session_state.current_step = 3; st.rerun()
            else: st.warning("❗ 请上传全部表格。")

# --- STEP 3 ---
elif st.session_state.current_step == 3:
    if "ocr_engine_inst" not in st.session_state:
        with st.status("🏗️ 初始化本地 OCR 引擎..."):
            from ocr_processor import OCRProcessor
            st.session_state.ocr_engine_inst = OCRProcessor()
    st.subheader("步骤 3: 采集审计样本证据")
    s1, s2 = st.columns(2)
    with s1: samples_file = st.file_uploader("方案 A: 样本清单", type=["csv", "xlsx", "xls"])
    with s2: voucher_images = st.file_uploader("方案 B: 凭证截图", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    if voucher_images:
        # Check if there are NEW images to process
        new_imgs = [img for img in voucher_images if img.name not in st.session_state.processed_image_names]
        if new_imgs:
            st.session_state.ocr_busy = True
            try:
                for img in new_imgs:
                    with st.status(f"🚀 解析: {img.name}...") as status:
                        img_bytes = img.getvalue()
                        llm_c = None
                        # Use DEFAULT_KEY if available
                        effective_key = DEFAULT_KEY
                        if effective_key:
                            from llm_client import LLMClient
                            llm_c = LLMClient(api_key=effective_key, model_name=selected_model)
                        res = st.session_state.ocr_engine_inst.process_and_parse(img_bytes, llm_client=llm_c)
                        if "items" in res:
                            for it in res["items"]:
                                if it.get("DOC_NUM") and str(it.get("DOC_NUM")).lower() != "null":
                                    item_id = f"{it.get('DOC_NUM')}_{it.get('SAKNR')}_{it.get('AMOUNT')}_{it.get('DATE')}"
                                    if item_id not in [f"{s.get('DOC_NUM')}_{s.get('SAKNR')}_{s.get('AMOUNT')}_{s.get('DATE')}" for s in st.session_state.ocr_samples]:
                                        st.session_state.ocr_samples.append(it)
                            st.session_state.processed_image_names.add(img.name)
                        status.update(label=f"✅ {img.name} 完成", state="complete")
            finally:
                st.session_state.ocr_busy = False
                st.rerun() # Refresh to enable button
    if st.session_state.ocr_samples:
        st.write("**📋 已录入样本预览**")
        st.dataframe(pd.DataFrame(st.session_state.ocr_samples), use_container_width=True)
    st.write("---")
    nav_cols = st.columns([1, 1.5, 1.5, 1])
    with nav_cols[1]:
        if st.button("返回上一步", use_container_width=True): st.session_state.current_step = 2; st.rerun()
    with nav_cols[2]:
        # Only enable button if ocr is not busy AND we have either a file or OCR samples
        btn_disabled = st.session_state.ocr_busy or (not samples_file and not st.session_state.ocr_samples)
        if st.button("🚀 生成最终底稿", use_container_width=True, disabled=btn_disabled):
            with st.spinner("AI 正在撰写穿行测试描述..."):
                if samples_file:
                    is_v, msg, s_df = DataValidator.validate_file(samples_file, "Samples")
                    if not is_v: st.error(msg); st.stop()
                else:
                    lines = []
                    for s in st.session_state.ocr_samples:
                        lines.append({"DOC_NUM": s.get("DOC_NUM"), "SAKNR": s.get("SAKNR"), "TXT50": s.get("TXT50"), "AMOUNT": s.get("AMOUNT"), "SHKZG": s.get("SHKZG", "S"), "DATE": s.get("DATE") or "2026-06-01"})
                    s_df = pd.DataFrame(lines)
                s_df.to_csv(os.path.join(SESSION_DATA_DIR, "Samples.csv"), index=False, encoding='utf-8-sig')
                
                c1 = Core1Orchestrator(SESSION_DATA_DIR); ranked = c1.run()
                
                # Debug: Show internal stats if results are weird
                if not ranked or sum(r['total_value'] for r in ranked) == 0:
                    st.warning(f"⚠️ 核心引擎警告: 未能匹配到任何活跃的审计场景。请检查上传清单的内容。")
                
                c2 = Core2Orchestrator(SESSION_DATA_DIR)
                # Use DEFAULT_KEY
                if DEFAULT_KEY:
                    from llm_client import LLMClient
                    c2.llm_client = LLMClient(api_key=DEFAULT_KEY, model_name=selected_model)
                
                di = c2.generate_di_descriptions(ranked, st.session_state.audit_context)
                
                if not di:
                    st.info("💡 提示：未能从上传的凭证截图或 Samples 列表中找到与审计场景匹配的样本项目。")
                
                gen = ReportGenerator(SESSION_DATA_DIR); path = gen.generate(ranked, di, st.session_state.audit_context)
                st.session_state.results = {"ranked": ranked, "di": di, "report_path": path}
                st.session_state.show_balloons = True; st.rerun()

st.write("---")
st.caption("© 2026 KPMG. All rights reserved. | IT Audit Technology & Innovation")
