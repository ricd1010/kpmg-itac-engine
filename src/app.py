import streamlit as st
import pandas as pd
import os
import datetime
import re
import hashlib
import base64
import io
import time
import uuid
import html
import textwrap
import streamlit.components.v1 as components
from core1_main import Core1Orchestrator
from core2_main import Core2Orchestrator
from report_generator_general import GeneralAuditReportGenerator as ReportGenerator
from data_validator import DataValidator
from scenario_summary import amount_for_direction, build_scenario_account_totals
from sampling_scenario import build_sampling_scenario_table
from sample_utils import (
    build_sample_voucher_index,
    enrich_samples_with_account_descriptions,
    is_duplicate_voucher_sample,
    load_account_description_map,
    remove_duplicate_ocr_samples,
)
from mm03_parser import mm03_records_to_dataframe_rows, parse_mm03_ocr_text
from voucher_validation import validate_voucher_t030_logic
from ledger_analysis import (
    analyze_ledger,
    build_exception_ledger,
    build_ledger_coverage_summary,
    build_ledger_dashboard_tables,
    ledger_display_dataframe,
)
from dotenv import load_dotenv

load_dotenv()
DEFAULT_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# KPMG Heritage Branding Colors
KPMG_BLUE = "#00338D"
KPMG_TEAL = "#00A3A1"
KPMG_DARK_GREY = "#1A1A1A"
KPMG_LIGHT_GREY = "#F7F9FC"
SCENARIO_PREVIEW_SCHEMA_VERSION = 16
PROJECT_CLASSIFIER_VERSION = "2026-07-02-sample-voucher-dedupe-v1"
SYSTEM_VERSION_OPTIONS = ["SAP ECC", "SAP S/4 HANA"]
AUTO_SCENARIO_LABEL = "自动识别"

# Generate custom KPMG Favicon
fav_svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
    <rect width="100" height="100" fill="{KPMG_BLUE}"/>
    <text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" font-family="Arial, sans-serif" font-weight="bold" font-size="70" fill="white">AC</text>
</svg>
"""
fav_b64 = base64.b64encode(fav_svg.encode()).decode()

st.set_page_config(
    page_title="TSDA 测试范围框定辅助驾驶舱",
    page_icon="🎯",
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
    
    /* Full Screen Width with Consistent Alignment Padding */
    .main .block-container {{
        max-width: 100% !important;
        padding: 2rem 3rem !important;
    }}
    
    [data-testid="stAppViewBlockContainer"] {{
        max-width: 100% !important;
        padding: 2rem 3rem !important;
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
    [data-testid="stSelectbox"] {{
        margin-top: -12px !important; /* Counter-act default invisible label space */
        margin-bottom: 0px !important;
    }}
    
    div[data-testid="column"]:nth-of-type(1) {{
        display: flex !important;
        align-items: center !important;
        height: 40px !important; /* Set a fixed height to align with selectbox */
    }}

    /* Forceful Header Typography */
    .kpmg-main-title {{
        color: #FFFFFF !important;
        font-size: 25px !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
        display: block !important;
        margin-bottom: 4px !important;
        font-family: 'Open Sans', sans-serif !important;
    }}

    .kpmg-sub-title {{
        color: #FFFFFF !important;
        font-size: 17px !important;
        font-weight: 400 !important;
        line-height: 1.2 !important;
        display: block !important;
        margin: 0 !important;
        opacity: 0.9 !important;
        font-family: 'Open Sans', sans-serif !important;
    }}
    
    /* Enforce Logo Dimensions */
    img.kpmg-header-logo {{
        height: 65px !important;
        min-height: 65px !important;
        max-height: 65px !important;
        width: auto !important;
        margin-right: 35px !important;
        transform: translateY(-2px) !important;
        display: block !important;
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
if "ocr_samples_editor_nonce" not in st.session_state: st.session_state.ocr_samples_editor_nonce = 0
if "sample_table_records" not in st.session_state: st.session_state.sample_table_records = []
if "sample_table_signature" not in st.session_state: st.session_state.sample_table_signature = None
if "sample_source_scenarios" not in st.session_state: st.session_state.sample_source_scenarios = {}
if "sample_dedupe_notice" not in st.session_state: st.session_state.sample_dedupe_notice = ""
if "processed_image_names" not in st.session_state: st.session_state.processed_image_names = set()
if "results" not in st.session_state: st.session_state.results = None
if "api_key_valid" not in st.session_state: st.session_state.api_key_valid = False
if "api_check_done" not in st.session_state: st.session_state.api_check_done = False
if "show_balloons" not in st.session_state: st.session_state.show_balloons = False
if "ocr_busy" not in st.session_state: st.session_state.ocr_busy = False
if "base_files_ready" not in st.session_state: st.session_state.base_files_ready = False
if "base_file_signature" not in st.session_state: st.session_state.base_file_signature = None
if "trial_balance_ready" not in st.session_state: st.session_state.trial_balance_ready = False
if "trial_balance_signature" not in st.session_state: st.session_state.trial_balance_signature = None
if "t001k_ready" not in st.session_state: st.session_state.t001k_ready = False
if "ledger_ready" not in st.session_state: st.session_state.ledger_ready = False
if "ledger_signature" not in st.session_state: st.session_state.ledger_signature = None
if "ledger_analysis_records" not in st.session_state: st.session_state.ledger_analysis_records = []
if "ledger_analysis_signature" not in st.session_state: st.session_state.ledger_analysis_signature = None
if "t001k_signature" not in st.session_state: st.session_state.t001k_signature = None
if "mm03_image_names" not in st.session_state: st.session_state.mm03_image_names = []
if "mm03_records" not in st.session_state: st.session_state.mm03_records = []
if "mm03_signature" not in st.session_state: st.session_state.mm03_signature = None
if "scenario_preview" not in st.session_state: st.session_state.scenario_preview = []
if "scenario_preview_schema_version" not in st.session_state: st.session_state.scenario_preview_schema_version = None
if "scroll_to_top" not in st.session_state: st.session_state.scroll_to_top = False
if "project_folder_loaded" not in st.session_state: st.session_state.project_folder_loaded = False
if "project_folder_signature" not in st.session_state: st.session_state.project_folder_signature = None
if "project_folder_manifest" not in st.session_state: st.session_state.project_folder_manifest = []
if "project_folder_summary" not in st.session_state: st.session_state.project_folder_summary = {}
if "project_pending_mm03_sources" not in st.session_state: st.session_state.project_pending_mm03_sources = []
if "project_pending_voucher_sources" not in st.session_state: st.session_state.project_pending_voucher_sources = []
if "audit_coverage_selected_keys" not in st.session_state: st.session_state.audit_coverage_selected_keys = set()
if "audit_coverage_target_pct" not in st.session_state: st.session_state.audit_coverage_target_pct = 80
if "audit_coverage_auto_seed_signature" not in st.session_state: st.session_state.audit_coverage_auto_seed_signature = None
if "project_auto_mm03_attempted" not in st.session_state: st.session_state.project_auto_mm03_attempted = False
if "project_auto_voucher_attempted" not in st.session_state: st.session_state.project_auto_voucher_attempted = False
if "voucher_validation_records" not in st.session_state: st.session_state.voucher_validation_records = []

def current_system_version():
    return st.session_state.audit_context.get("system_version") or st.session_state.audit_context.get("system_name") or "SAP S/4 HANA"

def is_s4_system():
    return "S/4" in current_system_version()

def go_to_step(step):
    st.session_state.current_step = step
    st.session_state.scroll_to_top = True
    st.rerun()

def render_scroll_to_top():
    if not st.session_state.get("scroll_to_top"):
        return
    st.session_state.scroll_to_top = False
    components.html(
        """
        <input
            id="scroll-focus-target"
            aria-hidden="true"
            autofocus
            style="width:1px;height:1px;opacity:0;border:0;padding:0;margin:0;"
        />
        <script>
        const focusTarget = document.getElementById("scroll-focus-target");
        const scrollTop = () => {
            try {
                window.focus();
                focusTarget.focus({ preventScroll: false });
                focusTarget.scrollIntoView({ block: "start", inline: "nearest" });
            } catch (err) {}
            try {
                window.parent.scrollTo({ top: 0, left: 0, behavior: "auto" });
                const doc = window.parent.document;
                const targets = [
                    doc.scrollingElement,
                    doc.documentElement,
                    doc.body,
                    doc.querySelector('[data-testid="stAppViewContainer"]'),
                    doc.querySelector('[data-testid="stAppViewBlockContainer"]'),
                    doc.querySelector('section.main'),
                    doc.querySelector('.main')
                ];
                targets.forEach((target) => {
                    if (target) {
                        target.scrollTop = 0;
                        target.scrollLeft = 0;
                    }
                });
            } catch (err) {}
        };
        scrollTop();
        window.requestAnimationFrame(scrollTop);
        [50, 150, 300, 600, 1000, 1500, 2500].forEach((delay) => window.setTimeout(scrollTop, delay));
        </script>
        """,
        height=1,
        width=1,
    )

render_scroll_to_top()

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

def upload_signature(*files):
    flat_files = []
    for item in files:
        if item is None:
            continue
        if isinstance(item, (list, tuple)):
            flat_files.extend(f for f in item if f is not None)
        else:
            flat_files.append(item)
    return tuple((f.name, getattr(f, "size", None)) for f in flat_files)

def validate_upload_to_session(uploaded_file, file_type):
    is_valid, msg, df = DataValidator.validate_file(uploaded_file, file_type)
    if is_valid:
        df.to_csv(os.path.join(SESSION_DATA_DIR, f"{file_type}.csv"), index=False, encoding="utf-8-sig")
    return is_valid, msg

def validate_uploads_to_session(uploaded_files, file_type):
    files = [f for f in (uploaded_files or []) if f is not None]
    if not files:
        return False, "未选择文件。", 0

    frames = []
    for uploaded_file in files:
        is_valid, msg, df = DataValidator.validate_file(uploaded_file, file_type)
        if not is_valid:
            return False, f"{uploaded_file.name}: {msg}", 0
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    combined.to_csv(os.path.join(SESSION_DATA_DIR, f"{file_type}.csv"), index=False, encoding="utf-8-sig")
    return True, "验证通过", len(files)

def load_session_table(file_type):
    path = os.path.join(SESSION_DATA_DIR, f"{file_type}.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception:
        return pd.DataFrame()

def session_table_exists(file_type):
    path = os.path.join(SESSION_DATA_DIR, f"{file_type}.csv")
    return os.path.exists(path) and os.path.getsize(path) > 0

def recover_loaded_session_state():
    if session_table_exists("T030") and session_table_exists("SKAT"):
        st.session_state.base_files_ready = True
        if st.session_state.base_file_signature is None:
            st.session_state.base_file_signature = ("session-cache", "T030", "SKAT")
    if session_table_exists("TrialBalance"):
        st.session_state.trial_balance_ready = True
        if st.session_state.trial_balance_signature is None:
            st.session_state.trial_balance_signature = ("session-cache", "TrialBalance")
    if session_table_exists("Ledger"):
        st.session_state.ledger_ready = True
        if st.session_state.ledger_signature is None:
            st.session_state.ledger_signature = ("session-cache", "Ledger")
    if session_table_exists("T001K"):
        st.session_state.t001k_ready = True
        if st.session_state.t001k_signature is None:
            st.session_state.t001k_signature = ("session-cache", "T001K")

def dataframe_to_excel_bytes(df, sheet_name="Sheet1"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return output.getvalue()

def save_uploaded_images(files, folder_name):
    target_dir = os.path.join(SESSION_DATA_DIR, folder_name)
    os.makedirs(target_dir, exist_ok=True)
    saved_names = []
    used_names = set()
    for uploaded in files or []:
        data = uploaded.getvalue()
        original_name = re.split(r"[\\/]", str(uploaded.name))[-1]
        stem, ext = os.path.splitext(original_name)
        safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._") or "image"
        safe_ext = re.sub(r"[^A-Za-z0-9.]+", "", ext.lower()) or ".png"
        digest = hashlib.sha1(data + original_name.encode("utf-8", errors="ignore")).hexdigest()[:8]
        safe_name = f"{safe_stem}_{digest}{safe_ext}"
        counter = 2
        while safe_name in used_names:
            safe_name = f"{safe_stem}_{digest}_{counter}{safe_ext}"
            counter += 1
        used_names.add(safe_name)
        with open(os.path.join(target_dir, safe_name), "wb") as f:
            f.write(data)
        saved_names.append(safe_name)
    return saved_names

def saved_image_path(folder_name, saved_name):
    target_dir = os.path.abspath(os.path.join(SESSION_DATA_DIR, folder_name))
    candidate = os.path.abspath(os.path.join(target_dir, os.path.basename(str(saved_name or ""))))
    if not candidate.startswith(target_dir + os.sep):
        raise ValueError("图片路径不在当前会话目录内")
    return candidate

def read_saved_image_bytes(folder_name, saved_name):
    path = saved_image_path(folder_name, saved_name)
    with open(path, "rb") as f:
        return f.read()

def save_project_image_sources(files, folder_name):
    saved_names = save_uploaded_images(files, folder_name)
    return [
        {
            "source_file": project_upload_display_name(uploaded),
            "saved_name": saved_name,
        }
        for uploaded, saved_name in zip(files or [], saved_names)
    ]

PROJECT_TYPE_LABELS = {
    "T030": "自动过账配置 T030",
    "SKAT": "科目主数据 SKAT",
    "TrialBalance": "科目余额/发生额表",
    "Ledger": "全量序时账/凭证明细",
    "T001K": "T001K 公司代码/评估分组",
    "Samples": "样本清单",
    "MM03": "MM03 物料主数据截图",
    "VoucherImage": "凭证截图",
    "Unclassified": "未识别",
}

PROJECT_SPREADSHEET_TYPES = ["T030", "SKAT", "TrialBalance", "Ledger", "T001K", "Samples"]
PROJECT_IMAGE_EXTS = {".png", ".jpg", ".jpeg"}
PROJECT_DATA_EXTS = {".csv", ".xlsx", ".xls", ".txt"}
TRIAL_BALANCE_NAME_HINTS = ["科余", "课余", "余额", "发生额", "余额表", "faglflext", "trial", "balance", "tb"]
LEDGER_NAME_HINTS = ["序时账", "凭证明细", "全量凭证", "明细账", "journal", "ledger", "bseg", "bkpf", "fbl3n", "line item"]
T030_NAME_HINTS = ["t030", "obyc", "自动过账", "过账配置", "配置表"]

def project_upload_display_name(uploaded_file):
    return str(getattr(uploaded_file, "name", "") or "未命名文件").replace("\\", "/")

def project_upload_basename(uploaded_file):
    return re.split(r"[\\/]", project_upload_display_name(uploaded_file))[-1]

def project_filename_score(name, file_type):
    text = str(name or "").lower()
    score_map = {
        "T030": T030_NAME_HINTS,
        "SKAT": ["skat", "科目主数据", "科目表", "总账科目表"],
        "TrialBalance": TRIAL_BALANCE_NAME_HINTS + ["acdoca"],
        "Ledger": LEDGER_NAME_HINTS,
        "T001K": ["t001k", "评估范围", "评估分组"],
        "Samples": ["sample", "samples", "样本", "fb03", "凭证", "清单", "inf"],
    }
    score = 0
    for keyword in score_map.get(file_type, []):
        if keyword and keyword.lower() in text:
            score += 30
    if file_type == "SKAT" and any(word in text for word in ["科余", "课余", "余额"]):
        score -= 40
    if file_type == "Samples" and any(word in text for word in ["t030", "skat", "t001k", "科余", "课余", "余额"]):
        score -= 30
    if file_type == "Samples" and any(word in text for word in ["序时账", "全量", "凭证明细", "bseg", "bkpf", "journal", "ledger"]):
        score -= 60
    if file_type == "Ledger" and any(word in text for word in ["sample", "samples", "样本", "fb03", "抽样"]):
        score -= 50
    return score

def project_preferred_type_from_filename(name):
    text = str(name or "").lower()
    strong_rules = [
        ("Ledger", LEDGER_NAME_HINTS),
        ("TrialBalance", TRIAL_BALANCE_NAME_HINTS + ["acdoca"]),
        ("T001K", ["t001k", "评估范围", "评估分组"]),
        ("T030", T030_NAME_HINTS),
        ("SKAT", ["skat", "科目主数据", "总账科目表"]),
        ("Samples", ["sample", "samples", "样本", "fb03", "凭证"]),
    ]
    for file_type, keywords in strong_rules:
        if any(keyword.lower() in text for keyword in keywords):
            return file_type
    return ""

def project_candidate_block_reason(name, file_type):
    text = str(name or "").lower()
    has_tb_hint = any(keyword.lower() in text for keyword in TRIAL_BALANCE_NAME_HINTS)
    has_ledger_hint = any(keyword.lower() in text for keyword in LEDGER_NAME_HINTS)
    has_t030_hint = any(keyword.lower() in text for keyword in T030_NAME_HINTS)
    if file_type == "T030" and (has_tb_hint or has_ledger_hint) and not has_t030_hint:
        return "文件名明确指向科目余额/发生额或序时账，禁止按 T030 兜底识别"
    if file_type in {"SKAT", "Samples"} and has_tb_hint:
        return "文件名明确指向科目余额/发生额，禁止按科目主数据或样本兜底识别"
    if file_type == "TrialBalance" and has_ledger_hint:
        return "文件名明确指向全量序时账，禁止按余额表兜底识别"
    return ""

def project_validate_candidate(uploaded_file, file_type):
    blocked = project_candidate_block_reason(project_upload_display_name(uploaded_file), file_type)
    if blocked:
        return {
            "file_type": file_type,
            "valid": False,
            "message": blocked,
            "rows": 0,
            "columns": 0,
            "score": -100,
        }
    try:
        uploaded_file.seek(0)
        is_valid, msg, df = DataValidator.validate_file(uploaded_file, file_type)
        uploaded_file.seek(0)
    except Exception as exc:
        is_valid, msg, df = False, str(exc), None
    row_count = int(len(df)) if is_valid and df is not None else 0
    col_count = int(len(df.columns)) if is_valid and df is not None else 0
    score = project_filename_score(project_upload_display_name(uploaded_file), file_type)
    if is_valid:
        score += 100 + min(row_count, 100) / 5 + min(col_count, 30)
    return {
        "file_type": file_type,
        "valid": bool(is_valid),
        "message": msg,
        "rows": row_count,
        "columns": col_count,
        "score": score,
    }

def classify_project_upload(uploaded_file):
    display_name = project_upload_display_name(uploaded_file)
    basename = project_upload_basename(uploaded_file)
    _, ext = os.path.splitext(basename.lower())
    name_text = display_name.lower()
    size = getattr(uploaded_file, "size", None)

    if basename.startswith("~$") or basename.startswith("."):
        return {
            "文件": display_name,
            "识别类型": PROJECT_TYPE_LABELS["Unclassified"],
            "detected_type": "Unclassified",
            "状态": "跳过",
            "原因": "临时文件或隐藏文件，不参与项目资料识别",
            "confidence": 0,
            "size": size,
        }

    if ext in PROJECT_IMAGE_EXTS:
        if any(token in name_text for token in ["mm03", "物料主数据", "material master", "material_master"]):
            detected_type = "MM03"
            reason = "文件名包含 MM03/物料主数据关键词"
            confidence = 95
        else:
            detected_type = "VoucherImage"
            reason = "图片文件，按凭证截图导入；如为 MM03 请在文件名中包含 MM03"
            confidence = 70
        return {
            "文件": display_name,
            "识别类型": PROJECT_TYPE_LABELS[detected_type],
            "detected_type": detected_type,
            "状态": "可加载",
            "原因": reason,
            "confidence": confidence,
            "size": size,
        }

    if ext not in PROJECT_DATA_EXTS:
        return {
            "文件": display_name,
            "识别类型": PROJECT_TYPE_LABELS["Unclassified"],
            "detected_type": "Unclassified",
            "状态": "跳过",
            "原因": f"暂不支持的文件类型：{ext or '未知'}",
            "confidence": 0,
            "size": size,
        }

    preferred_type = project_preferred_type_from_filename(display_name)
    candidate_types = [preferred_type] if preferred_type else PROJECT_SPREADSHEET_TYPES
    candidates = [project_validate_candidate(uploaded_file, file_type) for file_type in candidate_types]
    valid_candidates = [item for item in candidates if item["valid"]]
    if preferred_type and not valid_candidates:
        fallback_types = [file_type for file_type in PROJECT_SPREADSHEET_TYPES if file_type != preferred_type]
        fallback_candidates = [project_validate_candidate(uploaded_file, file_type) for file_type in fallback_types]
        candidates.extend(fallback_candidates)
        valid_candidates = [item for item in candidates if item["valid"]]
    if not valid_candidates:
        hint = max(candidates, key=lambda item: item["score"], default=None)
        reason = hint["message"] if hint else "未匹配到支持的清单字段"
        return {
            "文件": display_name,
            "识别类型": PROJECT_TYPE_LABELS["Unclassified"],
            "detected_type": "Unclassified",
            "状态": "需人工确认",
            "原因": reason,
            "confidence": 0,
            "size": size,
        }

    valid_by_type = {item["file_type"]: item for item in valid_candidates}
    if "TrialBalance" in valid_by_type and preferred_type in {"", "TrialBalance"}:
        chosen = valid_by_type["TrialBalance"]
    else:
        preferred_candidates = [item for item in valid_candidates if item["file_type"] == preferred_type]
        chosen = max(preferred_candidates or valid_candidates, key=lambda item: (item["score"], item["rows"], item["columns"]))
    return {
        "文件": display_name,
        "识别类型": PROJECT_TYPE_LABELS[chosen["file_type"]],
        "detected_type": chosen["file_type"],
        "状态": "可加载",
        "原因": f"字段校验通过；{chosen['rows']} 行，{chosen['columns']} 列",
        "confidence": round(float(chosen["score"]), 2),
        "size": size,
    }

def clear_project_imported_data():
    for file_type in ["T030", "SKAT", "TrialBalance", "Ledger", "Samples", "T001K"]:
        path = os.path.join(SESSION_DATA_DIR, f"{file_type}.csv")
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
    st.session_state.base_files_ready = False
    st.session_state.base_file_signature = None
    st.session_state.trial_balance_ready = False
    st.session_state.trial_balance_signature = None
    st.session_state.ledger_ready = False
    st.session_state.ledger_signature = None
    st.session_state.ledger_analysis_records = []
    st.session_state.ledger_analysis_signature = None
    st.session_state.t001k_ready = False
    st.session_state.t001k_signature = None
    st.session_state.mm03_image_names = []
    st.session_state.mm03_records = []
    st.session_state.mm03_signature = None
    st.session_state.project_pending_mm03_sources = []
    st.session_state.project_pending_voucher_sources = []
    st.session_state.project_auto_mm03_attempted = False
    st.session_state.project_auto_voucher_attempted = False
    st.session_state.sample_table_records = []
    st.session_state.sample_table_signature = None
    st.session_state.ocr_samples = []
    st.session_state.sample_dedupe_notice = ""
    st.session_state.processed_image_names = set()
    st.session_state.sample_source_scenarios = {}
    st.session_state.audit_coverage_selected_keys = set()
    st.session_state.audit_coverage_auto_seed_signature = None
    st.session_state.voucher_validation_records = []
    st.session_state.results = None
    st.session_state.scenario_preview = []
    st.session_state.scenario_preview_schema_version = None

def best_project_file(files):
    return sorted(files or [], key=lambda item: item[0].get("confidence", 0), reverse=True)[0][1] if files else None

def process_project_sample_files(sample_files):
    account_descriptions = load_account_description_map(SESSION_DATA_DIR)
    table_records = []
    errors = []
    for uploaded in sample_files or []:
        try:
            uploaded.seek(0)
            is_valid, msg, s_df = DataValidator.validate_file(uploaded, "Samples")
            uploaded.seek(0)
        except Exception as exc:
            is_valid, msg, s_df = False, str(exc), None
        if not is_valid:
            errors.append(f"{project_upload_display_name(uploaded)}: {msg}")
            continue
        s_df.columns = [str(col).strip().upper() for col in s_df.columns]
        s_records = enrich_samples_with_account_descriptions(s_df.to_dict("records"), account_descriptions)
        s_records = normalize_sample_preview_records(
            s_records,
            source_type="样本清单",
            source_file=project_upload_display_name(uploaded),
        )
        s_records = apply_scenario_to_records(s_records, AUTO_SCENARIO_LABEL, st.session_state.scenario_preview)
        table_records.extend(s_records)
    return table_records, errors

def process_project_mm03_images(mm03_images):
    if not mm03_images:
        return 0, []
    ocr_engine = get_ocr_engine()
    names = save_uploaded_images(mm03_images, "mm03")
    records = []
    errors = []
    for uploaded, saved_name in zip(mm03_images, names):
        try:
            image_bytes = uploaded.getvalue()
            parsed = ocr_engine.process_and_parse(image_bytes, llm_client=None)
            if "error" in parsed:
                record = parse_mm03_ocr_text("", saved_name)
                record["ocr_status"] = parsed["error"]
            else:
                record = parse_mm03_ocr_text(parsed.get("OCR_TEXT", ""), saved_name)
                record["ocr_status"] = "已解析"
            records.append(record)
        except Exception as exc:
            errors.append(f"{project_upload_display_name(uploaded)}: {exc}")
    st.session_state.mm03_image_names = names
    st.session_state.mm03_records = records
    st.session_state.mm03_signature = ("project-folder", upload_signature(mm03_images))
    return len(records), errors

def register_project_mm03_images(mm03_images):
    if not mm03_images:
        return 0, []
    sources = save_project_image_sources(mm03_images, "mm03")
    st.session_state.project_pending_mm03_sources = sources
    st.session_state.mm03_image_names = [item["saved_name"] for item in sources]
    st.session_state.mm03_records = []
    st.session_state.mm03_signature = ("project-folder-deferred", upload_signature(mm03_images))
    st.session_state.project_auto_mm03_attempted = False
    return len(sources), []

def process_pending_project_mm03_images():
    sources = st.session_state.get("project_pending_mm03_sources") or []
    if not sources:
        return 0, []
    ocr_engine = get_ocr_engine()
    records = []
    errors = []
    for source in sources:
        saved_name = source.get("saved_name", "")
        try:
            parsed = ocr_engine.process_and_parse(read_saved_image_bytes("mm03", saved_name), llm_client=None)
            if "error" in parsed:
                record = parse_mm03_ocr_text("", saved_name)
                record["ocr_status"] = parsed["error"]
            else:
                record = parse_mm03_ocr_text(parsed.get("OCR_TEXT", ""), saved_name)
                record["ocr_status"] = "已解析"
            records.append(record)
        except Exception as exc:
            errors.append(f"{source.get('source_file') or saved_name}: {exc}")
    st.session_state.mm03_records = records
    st.session_state.mm03_image_names = [item.get("saved_name", "") for item in sources]
    if records:
        st.session_state.project_pending_mm03_sources = []
    return len(records), errors

def register_project_voucher_images(voucher_images):
    if not voucher_images:
        return 0, []
    sources = save_project_image_sources(voucher_images, "vouchers")
    st.session_state.project_pending_voucher_sources = sources
    st.session_state.project_auto_voucher_attempted = False
    return len(sources), []

def process_voucher_image_sources(image_sources, selected_model):
    if not image_sources:
        return 0, []
    ocr_engine = get_ocr_engine()
    account_descriptions = load_account_description_map(SESSION_DATA_DIR)
    llm_c = None
    if DEFAULT_KEY:
        from llm_client import LLMClient
        llm_c = LLMClient(api_key=DEFAULT_KEY, model_name=selected_model)

    added = 0
    errors = []
    existing_ids = {
        f"{s.get('SOURCE_FILE')}_{s.get('DOC_NUM')}_{s.get('SAKNR')}_{s.get('AMOUNT')}_{s.get('DATE')}"
        for s in st.session_state.ocr_samples
    }
    table_voucher_index = build_sample_voucher_index(st.session_state.sample_table_records)
    skipped_duplicate_rows = 0
    for source in image_sources:
        source_file = source.get("source_file", "")
        try:
            image_bytes = source.get("bytes")
            if image_bytes is None:
                image_bytes = read_saved_image_bytes(source.get("folder", "vouchers"), source.get("saved_name", ""))
            res = ocr_engine.process_and_parse(image_bytes, llm_client=llm_c)
            if "items" not in res:
                errors.append(f"{source_file}: {res.get('error', '未识别到凭证明细')}")
                continue
            parsed_items = []
            for item in res["items"]:
                if item.get("DOC_NUM") and str(item.get("DOC_NUM")).lower() != "null":
                    parsed_items.append(enrich_samples_with_account_descriptions([item], account_descriptions)[0])
            parsed_items = normalize_sample_preview_records(
                parsed_items,
                source_type="凭证截图",
                source_file=source_file,
            )
            parsed_items = apply_scenario_to_records(parsed_items, AUTO_SCENARIO_LABEL, st.session_state.scenario_preview)
            for item in parsed_items:
                if is_duplicate_voucher_sample(item, table_voucher_index):
                    skipped_duplicate_rows += 1
                    continue
                item_id = f"{item.get('SOURCE_FILE')}_{item.get('DOC_NUM')}_{item.get('SAKNR')}_{item.get('AMOUNT')}_{item.get('DATE')}"
                if item_id not in existing_ids:
                    st.session_state.ocr_samples.append(item)
                    existing_ids.add(item_id)
                    added += 1
            if source_file:
                st.session_state.processed_image_names.add(source_file)
        except Exception as exc:
            errors.append(f"{source_file}: {exc}")
    if skipped_duplicate_rows:
        st.session_state.sample_dedupe_notice = (
            f"已识别到 {skipped_duplicate_rows} 行凭证截图 OCR 与样本清单凭证号重复；"
            "系统保留样本清单作为主样本来源，截图不再重复纳入样本范围。"
        )
    return added, errors

def process_pending_project_voucher_images(selected_model):
    sources = [
        {
            "source_file": source.get("source_file") or source.get("saved_name", ""),
            "saved_name": source.get("saved_name", ""),
            "folder": "vouchers",
        }
        for source in (st.session_state.get("project_pending_voucher_sources") or [])
    ]
    added, errors = process_voucher_image_sources(sources, selected_model)
    if added or not errors:
        st.session_state.project_pending_voucher_sources = []
    if added:
        st.session_state.ocr_samples_editor_nonce += 1
    return added, errors

def process_project_voucher_images(voucher_images, selected_model):
    if not voucher_images:
        return 0, []
    sources = [
        {
            "source_file": project_upload_display_name(img),
            "bytes": img.getvalue(),
        }
        for img in voucher_images
    ]
    return process_voucher_image_sources(sources, selected_model)

def process_project_folder_upload(project_files, selected_model):
    files = [file for file in (project_files or []) if file is not None]
    if not files:
        return {"loaded": False, "loaded_items": [], "warnings": ["未选择项目资料文件夹。"]}

    raw_signature = upload_signature(files)
    signature = (PROJECT_CLASSIFIER_VERSION, raw_signature)
    if st.session_state.project_folder_loaded and signature == st.session_state.project_folder_signature:
        return st.session_state.project_folder_summary

    clear_project_imported_data()

    manifest = []
    grouped = {key: [] for key in PROJECT_TYPE_LABELS}
    for uploaded in files:
        info = classify_project_upload(uploaded)
        manifest.append(info)
        detected_type = info.get("detected_type")
        if info.get("状态") == "可加载" and detected_type in grouped:
            grouped[detected_type].append((info, uploaded))

    st.session_state.project_folder_manifest = manifest
    loaded_items = []
    warnings = []

    t030_file = best_project_file(grouped["T030"])
    skat_file = best_project_file(grouped["SKAT"])
    if t030_file and skat_file:
        t030_ok, t030_msg = validate_upload_to_session(t030_file, "T030")
        skat_ok, skat_msg = validate_upload_to_session(skat_file, "SKAT")
        if t030_ok and skat_ok:
            st.session_state.base_files_ready = True
            st.session_state.base_file_signature = ("project-folder", signature, project_upload_display_name(t030_file), project_upload_display_name(skat_file))
            refresh_scenario_preview()
            loaded_items.append("T030/SKAT 场景映射")
        else:
            warnings.append(f"T030/SKAT 加载失败：T030={t030_msg}; SKAT={skat_msg}")
    else:
        warnings.append("未同时识别到 T030 与 SKAT，后续仍需补充自动过账配置和科目主数据。")

    trial_balance_files = [uploaded for _, uploaded in grouped["TrialBalance"]]
    if trial_balance_files:
        is_valid, msg, file_count = validate_uploads_to_session(trial_balance_files, "TrialBalance")
        if is_valid:
            st.session_state.trial_balance_ready = True
            st.session_state.trial_balance_signature = ("project-folder", signature, "TrialBalance", file_count)
            if st.session_state.base_files_ready:
                refresh_scenario_preview()
            loaded_items.append(f"{file_count} 张余额/发生额表")
        else:
            warnings.append(f"余额/发生额表加载失败：{msg}")

    ledger_files = [uploaded for _, uploaded in grouped["Ledger"]]
    if ledger_files:
        is_valid, msg, file_count = validate_uploads_to_session(ledger_files, "Ledger")
        if is_valid:
            st.session_state.ledger_ready = True
            st.session_state.ledger_signature = ("project-folder", signature, "Ledger", file_count)
            st.session_state.ledger_analysis_records = []
            loaded_items.append(f"{file_count} 张全量序时账/凭证明细")
        else:
            warnings.append(f"全量序时账/凭证明细加载失败：{msg}")

    t001k_file = best_project_file(grouped["T001K"])
    if t001k_file:
        t001k_ok, t001k_msg = validate_upload_to_session(t001k_file, "T001K")
        if t001k_ok:
            st.session_state.t001k_ready = True
            st.session_state.t001k_signature = ("project-folder", signature, project_upload_display_name(t001k_file))
            loaded_items.append("T001K 公司代码/评估分组")
        else:
            warnings.append(f"T001K 加载失败：{t001k_msg}")

    sample_files = [uploaded for _, uploaded in grouped["Samples"]]
    if sample_files:
        table_records, sample_errors = process_project_sample_files(sample_files)
        if sample_errors:
            warnings.extend(sample_errors)
        if table_records:
            st.session_state.sample_table_records = table_records
            st.session_state.ocr_samples, removed_ocr_samples = remove_duplicate_ocr_samples(
                st.session_state.sample_table_records,
                st.session_state.ocr_samples,
            )
            if removed_ocr_samples:
                st.session_state.sample_dedupe_notice = (
                    f"已识别到 {len(removed_ocr_samples)} 行凭证截图 OCR 与样本清单凭证号重复；"
                    "系统保留样本清单作为主样本来源，截图不再重复纳入样本范围。"
                )
            st.session_state.sample_table_signature = ("project-folder", signature, "Samples", len(sample_files))
            st.session_state.ocr_samples_editor_nonce += 1
            loaded_items.append(f"{len(sample_files)} 个样本清单文件 / {len(table_records)} 行")

    mm03_images = [uploaded for _, uploaded in grouped["MM03"]]
    if mm03_images:
        mm03_count, mm03_errors = register_project_mm03_images(mm03_images)
        warnings.extend(mm03_errors)
        if mm03_count:
            loaded_items.append(f"{mm03_count} 张 MM03 截图（已登记，Step 3 按需解析）")

    voucher_images = [uploaded for _, uploaded in grouped["VoucherImage"]]
    if voucher_images:
        voucher_count, voucher_errors = register_project_voucher_images(voucher_images)
        warnings.extend(voucher_errors)
        if voucher_count:
            loaded_items.append(f"{voucher_count} 张凭证截图（已登记，Step 3 按需 OCR）")

    combined_records = st.session_state.sample_table_records + st.session_state.ocr_samples
    if combined_records and st.session_state.scenario_preview:
        sync_source_scenarios_from_records(combined_records, scenario_names_from_preview())

    summary = {
        "loaded": True,
        "classifier_version": PROJECT_CLASSIFIER_VERSION,
        "loaded_items": loaded_items,
        "warnings": warnings,
        "file_count": len(files),
        "recognized_count": sum(1 for item in manifest if item.get("detected_type") != "Unclassified"),
    }
    st.session_state.project_folder_loaded = True
    st.session_state.project_folder_signature = signature
    st.session_state.project_folder_summary = summary
    return summary

def render_project_folder_status():
    manifest = st.session_state.get("project_folder_manifest") or []
    summary = st.session_state.get("project_folder_summary") or {}
    if not manifest and not summary:
        return

    if summary and summary.get("classifier_version") != PROJECT_CLASSIFIER_VERSION:
        st.warning("项目资料包识别规则已更新，请返回步骤 1 重新选择项目资料文件夹并点击下一步，以刷新自动识别结果。")
        return

    loaded_items = summary.get("loaded_items") or []
    warnings = summary.get("warnings") or []
    if loaded_items:
        st.success("项目资料包已自动加载：" + "、".join(loaded_items))
        st.caption(f"自动识别器版本：{PROJECT_CLASSIFIER_VERSION}")
    if warnings:
        st.warning("；".join(warnings[:6]))
    if manifest:
        with st.expander("查看项目资料包自动识别结果", expanded=True):
            manifest_df = pd.DataFrame(manifest)
            display_cols = ["文件", "识别类型", "状态", "原因"]
            for col in display_cols:
                if col not in manifest_df.columns:
                    manifest_df[col] = ""
            st.dataframe(manifest_df[display_cols], width="stretch", hide_index=True)

def refresh_scenario_preview():
    ranked = Core1Orchestrator(SESSION_DATA_DIR).run()
    st.session_state.scenario_preview = ranked
    st.session_state.scenario_preview_schema_version = SCENARIO_PREVIEW_SCHEMA_VERSION
    return ranked

def scenario_preview_needs_refresh():
    if not st.session_state.base_files_ready:
        return False
    if not os.path.exists(os.path.join(SESSION_DATA_DIR, "T030.csv")):
        return False
    if not os.path.exists(os.path.join(SESSION_DATA_DIR, "SKAT.csv")):
        return False
    if st.session_state.scenario_preview_schema_version != SCENARIO_PREVIEW_SCHEMA_VERSION:
        return True
    if st.session_state.trial_balance_ready:
        for result in st.session_state.scenario_preview:
            for item in result.get("company_values", []):
                if float(item.get("total_value", 0) or 0) and "account_values" not in item:
                    return True
    return False

def ensure_scenario_preview_current():
    if scenario_preview_needs_refresh():
        refresh_scenario_preview()

def clean_account_code(val):
    if pd.isna(val):
        return ""
    text = str(val).strip().split(".")[0]
    if not text or text.lower() in {"nan", "none", "null"}:
        return ""
    return text.lstrip("0") if text != "0" else "0"

def scenario_names_from_preview():
    return [str(row.get("name")) for row in st.session_state.scenario_preview if row.get("name")]

def scenario_account_lookup(ranked):
    lookup = {}
    for scenario in ranked or []:
        name = str(scenario.get("name", ""))
        if not name:
            continue
        accounts = set()
        for account in scenario.get("raw_accounts", []):
            code = clean_account_code(account)
            if code:
                accounts.add(code)
        if not accounts:
            for account in scenario.get("accounts", []):
                code = clean_account_code(str(account).split(" ")[0])
                if code:
                    accounts.add(code)
        lookup[name] = accounts
    return lookup

def infer_scenario_for_records(records, ranked):
    sample_accounts = {
        clean_account_code(record.get("SAKNR"))
        for record in records or []
        if clean_account_code(record.get("SAKNR"))
    }
    if not sample_accounts:
        return AUTO_SCENARIO_LABEL
    candidates = [
        name
        for name, accounts in scenario_account_lookup(ranked).items()
        if accounts.intersection(sample_accounts)
    ]
    return candidates[0] if len(candidates) == 1 else AUTO_SCENARIO_LABEL

def apply_scenario_to_records(records, selected_scenario, ranked):
    if not records:
        return []
    enriched = [dict(record) for record in records]
    if selected_scenario and selected_scenario != AUTO_SCENARIO_LABEL:
        for record in enriched:
            record["SCENARIO"] = selected_scenario
        return enriched

    by_doc = {}
    for record in enriched:
        by_doc.setdefault(str(record.get("DOC_NUM", "")), []).append(record)
    for rows in by_doc.values():
        inferred = infer_scenario_for_records(rows, ranked)
        for record in rows:
            if not record.get("SCENARIO"):
                record["SCENARIO"] = inferred
    return enriched

def apply_scenario_to_dataframe(df, selected_scenario, ranked):
    result = df.copy()
    result.columns = [str(col).strip().upper() for col in result.columns]
    if "SCENARIO" not in result.columns:
        result["SCENARIO"] = ""
    if selected_scenario and selected_scenario != AUTO_SCENARIO_LABEL:
        result["SCENARIO"] = selected_scenario
        return result

    records = apply_scenario_to_records(result.to_dict("records"), AUTO_SCENARIO_LABEL, ranked)
    return pd.DataFrame(records)

def normalize_sample_preview_records(records, source_type="", source_file=""):
    normalized = []
    for record in records or []:
        item = {str(k).strip().upper(): v for k, v in dict(record).items()}
        item["SCENARIO"] = str(item.get("SCENARIO", "") or "").strip()
        item["DOC_NUM"] = item.get("DOC_NUM", "")
        item["COMPANY_CODE"] = item.get("COMPANY_CODE", "")
        item["DATE"] = item.get("DATE", "")
        item["SAKNR"] = item.get("SAKNR", "")
        item["TXT50"] = item.get("TXT50", "")
        item["MATNR"] = item.get("MATNR", "")
        item["AMOUNT"] = item.get("AMOUNT", "")
        item["SHKZG"] = item.get("SHKZG", "")
        item["KTOSL"] = item.get("KTOSL", "")
        item["KOMOK"] = item.get("KOMOK", "")
        item["SOURCE_TYPE"] = item.get("SOURCE_TYPE", source_type)
        item["SOURCE_FILE"] = item.get("SOURCE_FILE", source_file)
        normalized.append(item)
    return normalized

def editor_text_value(value):
    if pd.isna(value):
        return ""
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return ""
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()

def prepare_sample_editor_dataframe(records, scenario_options, preferred_columns):
    df = pd.DataFrame(records or [])
    for col in preferred_columns:
        if col not in df.columns:
            df[col] = ""

    allowed_scenarios = set(scenario_options or [])
    df["SCENARIO"] = df["SCENARIO"].map(editor_text_value).apply(
        lambda value: value if value in allowed_scenarios else ""
    )
    for col in df.columns:
        if col != "SCENARIO":
            df[col] = df[col].map(editor_text_value)

    remaining_columns = [col for col in df.columns if col not in preferred_columns]
    return df[preferred_columns + remaining_columns]

def sample_source_key(source_type, source_file):
    return f"{str(source_type or '').strip()}::{str(source_file or '').strip()}"

def sample_source_groups(records):
    groups = {}
    for record in records or []:
        source_type = str(record.get("SOURCE_TYPE", "") or "").strip()
        source_file = str(record.get("SOURCE_FILE", "") or "").strip()
        key = sample_source_key(source_type, source_file)
        if key == "::":
            continue
        groups.setdefault(key, {
            "source_type": source_type or "样本",
            "source_file": source_file or "未命名来源",
            "records": [],
        })["records"].append(record)
    return groups

def infer_source_scenario(records, scenario_options):
    allowed = set(scenario_options or [])
    values = {
        str(record.get("SCENARIO", "") or "").strip()
        for record in records or []
        if str(record.get("SCENARIO", "") or "").strip() in allowed
    }
    return next(iter(values)) if len(values) == 1 else ""

def apply_source_scenarios(records, source_scenarios):
    updated = []
    for record in records or []:
        item = dict(record)
        key = sample_source_key(item.get("SOURCE_TYPE"), item.get("SOURCE_FILE"))
        scenario = str((source_scenarios or {}).get(key, "") or "").strip()
        if scenario:
            item["SCENARIO"] = scenario
        updated.append(item)
    return updated

def sync_source_scenarios_from_records(records, scenario_options):
    groups = sample_source_groups(records)
    current_keys = set(groups)
    st.session_state.sample_source_scenarios = {
        key: value
        for key, value in st.session_state.sample_source_scenarios.items()
        if key in current_keys
    }
    for key, info in groups.items():
        scenario = infer_source_scenario(info["records"], scenario_options)
        if scenario:
            st.session_state.sample_source_scenarios[key] = scenario

def render_sample_source_scenario_controls(records, scenario_options):
    groups = sample_source_groups(records)
    if not groups:
        return

    current_keys = set(groups)
    st.session_state.sample_source_scenarios = {
        key: value
        for key, value in st.session_state.sample_source_scenarios.items()
        if key in current_keys
    }

    st.write("**按上传文件指定审计场景**")
    st.caption("每个样本清单或凭证截图单独选择一个场景；选择后会自动填充该来源下的所有样本行，下方预览表仍可逐行微调。")
    placeholder = "请选择场景"
    columns = st.columns(min(3, max(1, len(groups))))
    changed = False
    for idx, (key, info) in enumerate(sorted(groups.items(), key=lambda item: item[1]["source_file"])):
        existing = st.session_state.sample_source_scenarios.get(key) or infer_source_scenario(info["records"], scenario_options)
        options = [placeholder] + list(scenario_options)
        index = options.index(existing) if existing in options else 0
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:12]
        with columns[idx % len(columns)]:
            selected = st.selectbox(
                f"{info['source_file']} ({info['source_type']}, {len(info['records'])} 行)",
                options,
                index=index,
                key=f"sample_source_scenario_{digest}",
            )
        value = "" if selected == placeholder else selected
        if st.session_state.sample_source_scenarios.get(key, "") != value:
            st.session_state.sample_source_scenarios[key] = value
            changed = True

    if changed:
        st.session_state.sample_table_records = apply_source_scenarios(
            st.session_state.sample_table_records,
            st.session_state.sample_source_scenarios,
        )
        st.session_state.ocr_samples = apply_source_scenarios(
            st.session_state.ocr_samples,
            st.session_state.sample_source_scenarios,
        )
        st.session_state.ocr_samples_editor_nonce += 1

def split_sample_preview_records(records):
    table_records = []
    image_records = []
    for record in records or []:
        item = dict(record)
        source_type = str(item.get("SOURCE_TYPE", "")).strip()
        if source_type == "样本清单":
            table_records.append(item)
        else:
            image_records.append(item)
    return table_records, image_records

def valid_sample_scenarios(records, scenario_options):
    allowed = set(scenario_options or [])
    invalid = []
    for idx, record in enumerate(records or [], start=1):
        scenario = str(record.get("SCENARIO", "")).strip()
        if scenario not in allowed:
            invalid.append(idx)
    return invalid

SCENARIO_PROCESS_GROUPS = {
    "销售发货": "销售与收款",
    "销售入账": "销售与收款",
    "销售成本结转": "销售与收款",
    "收款核销": "销售与收款",
    "采购收货": "采购与付款",
    "采购入账": "采购与付款",
    "生产领料": "存货与生产成本",
    "完工入库": "存货与生产成本",
    "工单差异": "存货与生产成本",
    "产成品差异": "存货与生产成本",
    "固定资产折旧": "固定资产与折旧",
}

def process_group_for_scenario(scenario_name):
    return SCENARIO_PROCESS_GROUPS.get(str(scenario_name or "").strip(), "其他")

def split_meta_values(value):
    text = str(value or "").strip()
    if not text:
        return []
    parts = re.split(r"\s*/\s*|[;,，；]+", text)
    cleaned = []
    for part in parts:
        item = part.strip()
        if item and item.lower() not in {"nan", "none", "null"} and item not in cleaned:
            cleaned.append(item)
    return cleaned

def scenario_account_detail_lookup(ranked):
    lookup = {}
    for scenario in ranked or []:
        scenario_name = str(scenario.get("name", "") or "").strip()
        for detail in scenario.get("account_details", []) or []:
            account_code = str(detail.get("account", "") or "").strip()
            if scenario_name and account_code:
                lookup[(scenario_name, account_code)] = detail
    return lookup

def subscenario_labels_for_detail(scenario_name, account_code="", description="", detail=None):
    scenario_name = str(scenario_name or "").strip()
    account_code = str(account_code or "").strip()
    description = str(description or "").strip()
    detail = detail or {}
    ktosl_values = {item.upper() for item in split_meta_values(detail.get("ktosl"))}
    komok_values = {item.upper() for item in split_meta_values(detail.get("komok"))}
    labels = []

    def add(label):
        if label and label not in labels:
            labels.append(label)

    if scenario_name == "销售发货":
        if {"VAX", "VAY"} & komok_values or "GBB" in ktosl_values:
            add("销售发货成本过账")
        if "GISS" in ktosl_values:
            add("销售发货消耗")
    elif scenario_name == "销售入账":
        if "REV" in ktosl_values:
            add("收入确认")
        if "MWS" in ktosl_values:
            add("销项税确认")
        if "AKTY" in ktosl_values:
            add("销售应收/暂估")
    elif scenario_name == "销售成本结转":
        if {"VAX", "VAY"} & komok_values or "GBB" in ktosl_values:
            add("销售成本结转")
    elif scenario_name == "收款核销":
        add("收款清账")
    elif scenario_name == "采购收货":
        if "WRX" in ktosl_values or "GR/IR" in description.upper():
            add("GR/IR 暂估")
        if "BSX" in ktosl_values or any(word in description for word in ["原材料", "库存商品", "半成品", "包装物", "周转材料"]):
            add("存货入库")
    elif scenario_name == "采购入账":
        if "WRX" in ktosl_values or "GR/IR" in description.upper():
            add("GR/IR 清账")
        if "VST" in ktosl_values or "进项" in description:
            add("进项税确认")
        if "AKTP" in ktosl_values or "应付" in description:
            add("应付入账")
    elif scenario_name == "生产领料":
        if {"VBO", "VBR"} & komok_values or "GBB" in ktosl_values:
            add("生产领料消耗")
        if "BSX" in ktosl_values:
            add("库存转出")
    elif scenario_name == "完工入库":
        if "AUF" in komok_values or account_code.startswith(("500108", "500109")):
            add("生产成本完工转出")
        if "BSX" in ktosl_values or any(word in description for word in ["库存商品", "半成品"]):
            add("产成品/半成品入库")
    elif scenario_name == "工单差异":
        if "PRD" in ktosl_values:
            if "采购" in description:
                add("采购差异")
            if "转物料" in description or "物料转" in description:
                add("物料转物料差异")
            if "跨工厂" in description:
                add("跨工厂转移差异")
            if "产出" in description:
                add("产出差异")
            add("工单差异")
        if "AUF" in komok_values:
            add("完工结转差异")
    elif scenario_name == "产成品差异":
        if "UMSK" in ktosl_values or "转物料" in description or "物料转" in description:
            add("物料转物料差异")
        if "PRA" in komok_values:
            add("产成品采购差异")
    elif scenario_name == "固定资产折旧":
        if "累计折旧" in description or account_code.startswith("1602"):
            add("累计折旧")
        else:
            add("折旧费用")

    if not labels and detail:
        ktosl_text = " / ".join(split_meta_values(detail.get("ktosl")))
        komok_text = " / ".join(split_meta_values(detail.get("komok")))
        if ktosl_text and komok_text:
            add(f"{ktosl_text}-{komok_text}")
        elif ktosl_text:
            add(ktosl_text)
    if not labels:
        add(scenario_name or "未分类子场景")
    return labels

def subscenario_labels_for_summary_row(summary_row, ranked):
    detail = scenario_account_detail_lookup(ranked).get((
        str(summary_row.get("scenario", "") or "").strip(),
        str(summary_row.get("account", "") or "").strip(),
    ), {})
    return subscenario_labels_for_detail(
        summary_row.get("scenario"),
        summary_row.get("account"),
        summary_row.get("description"),
        detail,
    )

def label_chips_html(labels, class_name="subscenario-chip"):
    return "".join(
        f"<span class='{class_name}'>{html.escape(str(label))}</span>"
        for label in labels or []
    )

def build_scenario_coverage_items(ranked, direction_filter="全部"):
    rows = []
    summary_rows = build_scenario_account_totals(ranked, direction_filter=direction_filter)
    overall_total = sum(float(row.get("total_value", 0) or 0) for row in summary_rows)
    for row in summary_rows:
        amount = float(row.get("total_value", 0) or 0)
        if not amount:
            continue
        scenario_name = str(row.get("scenario", "") or "").strip()
        account_code = str(row.get("account", "") or "").strip()
        subscenario_labels = subscenario_labels_for_summary_row(row, ranked)
        key_src = f"{scenario_name}|{account_code}|{';'.join(subscenario_labels)}|{direction_filter}"
        coverage_key = hashlib.md5(key_src.encode("utf-8")).hexdigest()[:16]
        rows.append({
            "覆盖项ID": coverage_key,
            "流程分类": process_group_for_scenario(scenario_name),
            "审计场景": scenario_name,
            "子场景标签": "；".join(subscenario_labels),
            "科目编码": account_code,
            "科目描述": str(row.get("description", "") or "").strip(),
            "金额": amount,
            "占整体": (amount / overall_total * 100) if overall_total else 0.0,
            "占场景": float(row.get("amount_share_pct", 0) or 0),
            "命中公司数": int(row.get("company_count", 0) or 0),
        })
    return pd.DataFrame(rows)

def build_account_quantity_coverage(ranked, trial_balance_df):
    if trial_balance_df is None or not hasattr(trial_balance_df, "empty") or trial_balance_df.empty:
        return None
    df = trial_balance_df.copy()
    df.columns = [str(col).strip().upper() for col in df.columns]
    if "SAKNR" not in df.columns:
        return None
    account_series = (
        df["SAKNR"].astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )
    all_accounts = {
        account.lstrip("0") if account != "0" else "0"
        for account in account_series
        if account and account.lower() not in {"nan", "none", "null"}
    }
    scenario_accounts = {
        str(account).strip().lstrip("0") if str(account).strip() != "0" else "0"
        for scenario in ranked or []
        for account in (scenario.get("amount_accounts") or scenario.get("raw_accounts") or [])
        if str(account).strip()
    }
    matched_accounts = all_accounts.intersection(scenario_accounts)
    unmatched_accounts = all_accounts.difference(scenario_accounts)
    return {
        "total_accounts": len(all_accounts),
        "matched_accounts": len(matched_accounts),
        "unmatched_accounts": len(unmatched_accounts),
        "coverage_pct": (len(matched_accounts) / len(all_accounts) * 100) if all_accounts else 0.0,
        "matched_account_codes": sorted(matched_accounts),
        "unmatched_account_codes": sorted(unmatched_accounts),
    }

def render_account_quantity_coverage(ranked):
    tb_df = load_session_table("TrialBalance")
    coverage = build_account_quantity_coverage(ranked, tb_df)
    if not coverage:
        return

    st.markdown("### 自动科目识别看板")
    st.caption("以科目余额/发生额表中的唯一科目为基数，统计有多少科目已经落入当前自动分录场景范围。目标用于辅助判断自动凭证测试覆盖面，不替代审计判断。")
    metric_cols = st.columns(4)
    metric_cols[0].metric("科余表科目数", f"{coverage['total_accounts']}")
    metric_cols[1].metric("命中规定场景科目", f"{coverage['matched_accounts']}")
    metric_cols[2].metric("数量占比", f"{coverage['coverage_pct']:.2f}%")
    metric_cols[3].metric("未命中科目", f"{coverage['unmatched_accounts']}")

    if coverage["coverage_pct"] >= 90:
        st.success("已识别出 90% 以上客户科目与当前自动分录场景的关系，可进入样本覆盖范围筛选。")
    else:
        st.warning("当前科目数量覆盖率低于 90%。可补充固定资产、税费、人工、费用分摊等场景规则，或检查客户科目描述和配置表完整性。")

def current_ledger_analysis_signature():
    return (
        st.session_state.get("ledger_signature"),
        st.session_state.get("scenario_preview_schema_version"),
        tuple((row.get("name"), tuple(row.get("raw_accounts", [])), tuple(row.get("amount_accounts", []))) for row in st.session_state.get("scenario_preview", [])),
        st.session_state.get("t001k_signature"),
        st.session_state.get("mm03_signature"),
        len(st.session_state.get("mm03_records", []) or []),
    )

def ensure_ledger_analysis_current(ranked):
    if not st.session_state.get("ledger_ready"):
        st.session_state.ledger_analysis_records = []
        st.session_state.ledger_analysis_signature = None
        return pd.DataFrame()

    signature = current_ledger_analysis_signature()
    if st.session_state.get("ledger_analysis_records") and st.session_state.get("ledger_analysis_signature") == signature:
        return pd.DataFrame(st.session_state.ledger_analysis_records)

    ledger_df = load_session_table("Ledger")
    if ledger_df.empty:
        st.session_state.ledger_analysis_records = []
        st.session_state.ledger_analysis_signature = signature
        return pd.DataFrame()

    analysis_df = analyze_ledger(
        ledger_df,
        ranked,
        load_session_table("T030"),
        load_session_table("T001K"),
        st.session_state.mm03_records,
    )
    st.session_state.ledger_analysis_records = analysis_df.to_dict("records") if not analysis_df.empty else []
    st.session_state.ledger_analysis_signature = signature
    return analysis_df

def render_full_ledger_testing_dashboard(ranked):
    if not st.session_state.get("ledger_ready"):
        st.info("如需执行报告所述的全量实质性测试覆盖，请上传全量序时账/凭证明细表。当前仍可基于科目余额/发生额表进行金额影响分析。")
        return pd.DataFrame()

    with st.spinner("正在基于全量序时账执行场景归类与 T030 配置验证..."):
        analysis_df = ensure_ledger_analysis_current(ranked)
    if analysis_df.empty:
        st.warning("全量序时账已加载，但未能形成可分析的凭证明细。请检查凭证号、科目、金额等字段。")
        return analysis_df

    summary = build_ledger_coverage_summary(analysis_df)
    tables = build_ledger_dashboard_tables(analysis_df)
    exception_df = build_exception_ledger(analysis_df)
    display_df = ledger_display_dataframe(analysis_df)

    st.markdown("### 全量自动化凭证实质性测试覆盖")
    st.caption("基于全量序时账逐行识别自动分录场景，并结合公司代码、物料号、T001K/MM03 与 T030 配置判断是否可作为已完成实质性测试覆盖。")
    metric_cols = st.columns(5)
    metric_cols[0].metric("凭证行数", f"{summary['total_lines']:,}")
    metric_cols[1].metric("已覆盖行数", f"{summary['covered_lines']:,}")
    metric_cols[2].metric("金额覆盖率", f"{summary['amount_coverage_pct']:.2f}%")
    metric_cols[3].metric("科目覆盖率", f"{summary['account_coverage_pct']:.2f}%")
    metric_cols[4].metric("异常/未覆盖行数", f"{summary['exception_lines']:,}")

    if summary["amount_coverage_pct"] >= 90:
        st.success("全量凭证明细中已有 90% 以上金额可落入自动化凭证实质性测试覆盖。")
    else:
        st.warning("全量凭证明细金额覆盖率低于 90%，建议优先查看异常凭证清单，补充事务字段、物料主数据或扩展场景规则。")

    detail_cols = st.columns([1.15, 0.85])
    with detail_cols[0]:
        scenario_table = tables.get("scenario", pd.DataFrame())
        if not scenario_table.empty:
            st.markdown("**按场景与测试状态汇总**")
            scenario_display = scenario_table.copy()
            scenario_display["金额"] = scenario_display["金额"].map(lambda value: f"{float(value):,.2f}")
            st.dataframe(scenario_display, width="stretch", hide_index=True)
    with detail_cols[1]:
        exception_table = tables.get("exception", pd.DataFrame())
        if not exception_table.empty:
            st.markdown("**未覆盖/异常原因汇总**")
            exception_display = exception_table.copy()
            exception_display["金额"] = exception_display["金额"].map(lambda value: f"{float(value):,.2f}")
            st.dataframe(exception_display, width="stretch", hide_index=True)

    export_cols = st.columns([1.1, 1.1, 2.8])
    with export_cols[0]:
        st.download_button(
            "📥 下载异常凭证清单",
            data=dataframe_to_excel_bytes(exception_df, "异常凭证清单"),
            file_name="VAST_Exception_Vouchers.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
            disabled=exception_df.empty,
        )
    with export_cols[1]:
        st.download_button(
            "📥 下载全量标签序时账",
            data=dataframe_to_excel_bytes(display_df, "全量标签序时账"),
            file_name="VAST_Tagged_Ledger.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
            disabled=display_df.empty,
        )
    with export_cols[2]:
        st.caption("异常清单包括无法匹配自动化场景、多场景候选、配置不一致和字段待补充的凭证明细，供审计团队进一步核查手工或异常凭证。")

    with st.expander("预览异常凭证清单", expanded=False):
        if exception_df.empty:
            st.success("当前全量序时账未发现未覆盖或配置异常凭证明细。")
        else:
            st.dataframe(exception_df.head(200), width="stretch", hide_index=True)
    return analysis_df

def build_subscenario_rank_rows(coverage_df):
    if coverage_df.empty:
        return pd.DataFrame()
    expanded_rows = []
    scenario_totals = coverage_df.groupby("审计场景")["金额"].sum().to_dict()
    overall_total = float(coverage_df["金额"].sum())
    for _, row in coverage_df.iterrows():
        labels = [label.strip() for label in str(row.get("子场景标签", "")).split("；") if label.strip()]
        if not labels:
            labels = ["未分类子场景"]
        allocated_amount = float(row.get("金额", 0) or 0) / len(labels)
        for label in labels:
            expanded_rows.append({
                "审计场景": row.get("审计场景"),
                "子场景": label,
                "金额": allocated_amount,
            })
    expanded_df = pd.DataFrame(expanded_rows)
    grouped = expanded_df.groupby(["审计场景", "子场景"], as_index=False)["金额"].sum()
    grouped["占整体"] = grouped["金额"].apply(lambda value: (float(value) / overall_total * 100) if overall_total else 0.0)
    grouped["占场景"] = grouped.apply(
        lambda row: (float(row["金额"]) / float(scenario_totals.get(row["审计场景"], 0) or 0) * 100)
        if scenario_totals.get(row["审计场景"]) else 0.0,
        axis=1,
    )
    return grouped.sort_values("金额", ascending=False)

def render_testing_coverage_dashboard(ranked):
    coverage_df = build_scenario_coverage_items(ranked)
    if coverage_df.empty:
        return

    st.markdown(
        """
        <style>
        .coverage-hero-card {
            border: 1px solid #d7e2f0;
            border-radius: 8px;
            background: #ffffff;
            padding: 18px 20px;
            min-height: 228px;
            box-shadow: 0 6px 18px rgba(0, 51, 141, 0.08);
        }
        .coverage-hero-label {
            color: #4d5a6a;
            font-weight: 700;
            font-size: 14px;
        }
        .coverage-hero-value {
            color: #00338d;
            font-weight: 800;
            font-size: 52px;
            line-height: 1.05;
            margin-top: 6px;
        }
        .coverage-hero-sub {
            color: #0b6f6d;
            font-weight: 700;
            margin-top: 6px;
        }
        .coverage-hero-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
            margin-top: 16px;
            color: #4d5a6a;
            font-size: 13px;
        }
        .coverage-hero-grid span {
            display: flex;
            justify-content: space-between;
            border-top: 1px solid #edf1f7;
            padding-top: 7px;
        }
        .process-card-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 10px 0 16px 0;
        }
        .process-card {
            background: #00338D;
            border-radius: 8px;
            padding: 14px 16px;
            color: #ffffff;
            min-height: 112px;
            box-shadow: 0 6px 18px rgba(0, 51, 141, 0.12);
        }
        .process-card:nth-child(1) { background: #00338D; }
        .process-card:nth-child(2) { background: #005EB8; }
        .process-card:nth-child(3) { background: #007C89; }
        .process-card:nth-child(4) { background: #2E2E2E; }
        .process-card-title {
            font-size: 18px;
            font-weight: 800;
            margin-bottom: 6px;
        }
        .process-card-amount {
            font-size: 20px;
            font-weight: 800;
            margin-bottom: 8px;
        }
        .process-card-meta {
            display: flex;
            justify-content: space-between;
            gap: 8px;
            font-size: 12px;
            opacity: 0.95;
        }
        .coverage-status {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 6px 10px;
            font-weight: 800;
            font-size: 13px;
            margin-top: 10px;
        }
        .coverage-status-ok {
            color: #006341;
            background: #E4F4EC;
            border: 1px solid #A6D9BE;
        }
        .coverage-status-gap {
            color: #8A5A00;
            background: #FFF4D8;
            border: 1px solid #F1C66A;
        }
        @media (max-width: 1100px) {
            .process-card-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        @media (max-width: 720px) {
            .process-card-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("### 审计测试覆盖 Dashboard")
    st.caption("按已识别测试场景和子场景颗粒度选择拟测试范围，实时查看已选项目覆盖整体金额的比例。流程分类仅用于阅读，不作为聚合口径。")

    scenario_rank = (
        coverage_df.groupby("审计场景", as_index=False)["金额"]
        .sum()
        .sort_values("金额", ascending=False)
    )
    total_amount = float(coverage_df["金额"].sum())
    scenario_rank["占整体"] = scenario_rank["金额"].apply(lambda value: (float(value) / total_amount * 100) if total_amount else 0.0)
    subscenario_rank = build_subscenario_rank_rows(coverage_df)
    selected_keys = set(st.session_state.get("audit_coverage_selected_keys", set()))

    control_cols = st.columns([1.3, 1, 1, 1.2])
    target_pct = int(control_cols[0].slider(
        "最低风险覆盖要求",
        min_value=0,
        max_value=100,
        step=5,
        key="audit_coverage_target_pct",
    ))
    target_amount = total_amount * target_pct / 100 if total_amount else 0.0
    coverage_signature = tuple(coverage_df["覆盖项ID"].astype(str).tolist())
    if (
        not selected_keys
        and target_pct > 0
        and st.session_state.get("audit_coverage_auto_seed_signature") != coverage_signature
    ):
        auto_keys = set()
        auto_amount = 0.0
        for _, row in coverage_df.sort_values("金额", ascending=False).iterrows():
            if auto_amount >= target_amount:
                break
            auto_keys.add(str(row["覆盖项ID"]))
            auto_amount += float(row.get("金额", 0) or 0)
        st.session_state.audit_coverage_selected_keys = auto_keys
        st.session_state.audit_coverage_auto_seed_signature = coverage_signature
        selected_keys = auto_keys
    if control_cols[1].button("选择 Top 5 覆盖项", width="stretch"):
        st.session_state.audit_coverage_selected_keys = set(
            coverage_df.sort_values("金额", ascending=False).head(5)["覆盖项ID"].astype(str)
        )
        st.session_state.audit_coverage_auto_seed_signature = coverage_signature
        st.rerun()
    if control_cols[2].button("补足至目标覆盖率", width="stretch"):
        updated_keys = set(selected_keys)
        current_amount = float(coverage_df[coverage_df["覆盖项ID"].astype(str).isin(updated_keys)]["金额"].sum())
        for _, row in coverage_df[~coverage_df["覆盖项ID"].astype(str).isin(updated_keys)].sort_values("金额", ascending=False).iterrows():
            if current_amount >= target_amount:
                break
            updated_keys.add(str(row["覆盖项ID"]))
            current_amount += float(row.get("金额", 0) or 0)
        st.session_state.audit_coverage_selected_keys = updated_keys
        st.session_state.audit_coverage_auto_seed_signature = coverage_signature
        st.rerun()
    if control_cols[3].button("清空选择", width="stretch"):
        st.session_state.audit_coverage_selected_keys = set()
        st.session_state.audit_coverage_auto_seed_signature = coverage_signature
        st.rerun()
    process_cards_slot = st.empty()

    layout_cols = st.columns([1.25, 0.75])
    with layout_cols[0]:
        st.markdown("**大场景金额占比排名**")
        st.bar_chart(scenario_rank.set_index("审计场景")["金额"])
        sub_display = subscenario_rank.head(10).copy()
        display_count = len(sub_display)
        st.markdown(f"**子场景占比排名 Top {display_count}**")
        if display_count < 10:
            st.caption(f"当前筛选范围内只有 {display_count} 个可归类子场景，因此未显示满 10 条。")
        sub_display["金额"] = sub_display["金额"].map(lambda value: f"{float(value):,.2f}")
        sub_display["占整体"] = sub_display["占整体"].map(lambda value: f"{float(value):.2f}%")
        sub_display["占场景"] = sub_display["占场景"].map(lambda value: f"{float(value):.2f}%")
        st.dataframe(sub_display, width="stretch", hide_index=True)

    hero_slot = layout_cols[1].empty()
    editor_df = coverage_df.copy()
    editor_df.insert(0, "纳入测试范围", editor_df["覆盖项ID"].astype(str).isin(selected_keys))
    editor_df["金额"] = editor_df["金额"].round(2)
    editor_df["占整体"] = editor_df["占整体"].round(2)
    editor_df["占场景"] = editor_df["占场景"].round(2)
    editor_cols = [
        "纳入测试范围", "覆盖项ID", "流程分类", "审计场景", "子场景标签",
        "科目编码", "科目描述", "金额", "占整体", "占场景", "命中公司数",
    ]
    edited_df = st.data_editor(
        editor_df[editor_cols],
        width="stretch",
        hide_index=True,
        key="audit_coverage_editor",
        column_config={
            "覆盖项ID": None,
            "纳入测试范围": st.column_config.CheckboxColumn("已选"),
            "金额": st.column_config.NumberColumn("金额", format="%.2f"),
            "占整体": st.column_config.NumberColumn("占整体 %", format="%.2f"),
            "占场景": st.column_config.NumberColumn("占场景 %", format="%.2f"),
        },
        disabled=[col for col in editor_cols if col != "纳入测试范围"],
    )
    selected_keys = set(edited_df.loc[edited_df["纳入测试范围"], "覆盖项ID"].astype(str))
    st.session_state.audit_coverage_selected_keys = selected_keys
    selected_df = coverage_df[coverage_df["覆盖项ID"].astype(str).isin(selected_keys)]
    selected_amount = float(selected_df["金额"].sum()) if not selected_df.empty else 0.0
    selected_pct = (selected_amount / total_amount * 100) if total_amount else 0.0
    selected_scenarios = int(selected_df["审计场景"].nunique()) if not selected_df.empty else 0
    selected_subscenarios = len({
        label.strip()
        for labels in selected_df["子场景标签"].tolist()
        for label in str(labels).split("；")
        if label.strip()
    }) if not selected_df.empty else 0
    achieved_target = selected_pct >= target_pct
    gap_amount = max(target_amount - selected_amount, 0.0)

    process_stats = (
        coverage_df.groupby("流程分类", as_index=False)
        .agg(金额=("金额", "sum"), 覆盖项=("覆盖项ID", "count"), 场景=("审计场景", "nunique"))
        .sort_values("金额", ascending=False)
    )
    selected_process_amounts = (
        selected_df.groupby("流程分类")["金额"].sum().to_dict()
        if not selected_df.empty else {}
    )
    process_cards = []
    for _, row in process_stats.iterrows():
        process_name = str(row["流程分类"] or "其他")
        process_amount = float(row["金额"] or 0)
        selected_process_amount = float(selected_process_amounts.get(process_name, 0) or 0)
        process_selected_pct = (selected_process_amount / process_amount * 100) if process_amount else 0.0
        process_cards.append(
            "<div class='process-card'>"
            f"<div class='process-card-title'>{html.escape(process_name)}</div>"
            f"<div class='process-card-amount'>{process_amount:,.0f}</div>"
            "<div class='process-card-meta'>"
            f"<span>{int(row['场景'])} 个场景</span>"
            f"<span>{int(row['覆盖项'])} 个覆盖项</span>"
            f"<span>已选 {process_selected_pct:.1f}%</span>"
            "</div>"
            "</div>"
        )
    with process_cards_slot.container():
        st.markdown("**流程维度概览**")
        st.markdown(
            f"<div class='process-card-grid'>{''.join(process_cards)}</div>",
            unsafe_allow_html=True,
        )

    with hero_slot.container():
        status_class = "coverage-status-ok" if achieved_target else "coverage-status-gap"
        status_text = "已达到最低风险要求" if achieved_target else "未达到最低风险要求"
        gap_text = "无需补足" if achieved_target else f"还需覆盖 {gap_amount:,.2f}"
        st.markdown(
            f"""
            <div class="coverage-hero-card">
                <div class="coverage-hero-label">当前已选覆盖率</div>
                <div class="coverage-hero-value">{selected_pct:.2f}%</div>
                <div class="coverage-hero-sub">已选金额 {selected_amount:,.2f}</div>
                <div class="coverage-status {status_class}">{status_text}</div>
                <div class="coverage-hero-grid">
                    <span>最低要求 <strong>{target_pct}%</strong></span>
                    <span>覆盖缺口 <strong>{gap_text}</strong></span>
                    <span>已选覆盖项 <strong>{len(selected_keys)}</strong></span>
                    <span>覆盖场景 <strong>{selected_scenarios}</strong></span>
                    <span>覆盖子场景 <strong>{selected_subscenarios}</strong></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not selected_df.empty:
            selected_brief = selected_df[["审计场景", "子场景标签", "科目编码", "占整体"]].copy()
            selected_brief["占整体"] = selected_brief["占整体"].map(lambda value: f"{float(value):.2f}%")
            st.dataframe(selected_brief.head(8), width="stretch", hide_index=True)

    unselected_df = coverage_df[~coverage_df["覆盖项ID"].astype(str).isin(selected_keys)].sort_values("金额", ascending=False)
    if not unselected_df.empty:
        unselected_display = unselected_df.head(10).copy()
        unselected_count = len(unselected_display)
        st.markdown(f"**未选择测试范围金额排名 Top {unselected_count}**")
        if not achieved_target:
            st.caption("以下项目尚未纳入测试范围，可优先补选以满足最低风险覆盖要求。")
        else:
            st.caption("已达到当前覆盖要求；下列项目为尚未纳入测试范围的剩余重大项目。")
        unselected_cols = ["流程分类", "审计场景", "子场景标签", "科目编码", "科目描述", "金额", "占整体", "占场景"]
        unselected_display = unselected_display[unselected_cols]
        unselected_display["金额"] = unselected_display["金额"].map(lambda value: f"{float(value):,.2f}")
        unselected_display["占整体"] = unselected_display["占整体"].map(lambda value: f"{float(value):.2f}%")
        unselected_display["占场景"] = unselected_display["占场景"].map(lambda value: f"{float(value):.2f}%")
        st.dataframe(unselected_display, width="stretch", hide_index=True)
    else:
        st.success("所有覆盖项均已纳入测试范围。")

def build_audit_dashboard_rows(ranked):
    rows = []
    detail_lookup = scenario_account_detail_lookup(ranked)
    for scenario in ranked or []:
        scenario_name = str(scenario.get("name", "") or "").strip()
        for company in scenario.get("company_values", []) or []:
            company_code = str(company.get("company_code", "未指定公司") or "未指定公司")
            for account in company.get("account_values", []) or []:
                debit_value = float(amount_for_direction(account, "借方") or 0)
                credit_value = float(amount_for_direction(account, "贷方") or 0)
                total_value = float(amount_for_direction(account, "全部") or 0)
                if not (debit_value or credit_value or total_value):
                    continue
                account_code = str(account.get("account", "") or "").strip()
                description = str(account.get("description", "未知科目") or "未知科目").strip()
                detail = detail_lookup.get((scenario_name, account_code), {})
                rows.append({
                    "流程分类": process_group_for_scenario(scenario_name),
                    "审计场景": scenario_name,
                    "公司代码": company_code,
                    "子场景标签": "；".join(subscenario_labels_for_detail(scenario_name, account_code, description, detail)),
                    "科目编码": account_code,
                    "科目描述": description,
                    "借方金额": debit_value,
                    "贷方金额": credit_value,
                    "合计金额": total_value,
                })
    return pd.DataFrame(rows)

def build_config_mapping_rows(ranked):
    rows = []
    for scenario in ranked or []:
        scenario_name = str(scenario.get("name", "") or "").strip()
        for detail in scenario.get("account_details", []) or []:
            account_code = str(detail.get("account", "") or "").strip()
            description = str(detail.get("description", "未知科目") or "未知科目").strip()
            rows.append({
                "流程分类": process_group_for_scenario(scenario_name),
                "审计场景": scenario_name,
                "子场景标签": "；".join(subscenario_labels_for_detail(scenario_name, account_code, description, detail)),
                "科目编码": account_code,
                "科目描述": description,
                "配置借贷方": str(detail.get("direction", "") or "").strip(),
                "匹配状态": "未匹配科目名称" if "未知科目" in str(detail.get("description", "")) else "已匹配",
            })
        if not scenario.get("account_details"):
            for account in scenario.get("accounts", []) or []:
                account_text = str(account)
                rows.append({
                    "流程分类": process_group_for_scenario(scenario_name),
                    "审计场景": scenario_name,
                    "子场景标签": "；".join(subscenario_labels_for_detail(scenario_name, account_text.split(" ")[0], account_text, {})),
                    "科目编码": account_text.split(" ")[0],
                    "科目描述": account_text,
                    "配置借贷方": "",
                    "匹配状态": "未匹配科目名称" if "未知科目" in account_text else "已匹配",
                })
    return pd.DataFrame(rows)

def render_general_audit_dashboard(ranked):
    dashboard_df = build_audit_dashboard_rows(ranked)
    if dashboard_df.empty:
        mapping_df = build_config_mapping_rows(ranked)
        scenario_count = len(ranked or [])
        account_count = int(len(mapping_df)) if not mapping_df.empty else 0
        unmatched_count = int((mapping_df["匹配状态"] == "未匹配科目名称").sum()) if not mapping_df.empty else 0
        matched_count = max(account_count - unmatched_count, 0)

        st.markdown("### 审计价值 Dashboard")
        st.caption("已完成 SAP 自动分录配置到财务科目的映射。上传科目余额/发生额表后，将进一步量化各场景对财务报表科目的影响。")
        metric_cols = st.columns(4)
        metric_cols[0].metric("识别业务场景", f"{scenario_count}")
        metric_cols[1].metric("配置关联科目", f"{account_count}")
        metric_cols[2].metric("已匹配科目名称", f"{matched_count}")
        metric_cols[3].metric("待补充科目名称", f"{unmatched_count}")

        st.info(
            "审计价值摘要：当前已把 SAP 自动过账配置转化为可审计的业务场景与财务科目清单。"
            "下一步补充金额表后，系统会自动生成场景金额排行、重点科目贡献、科目数量覆盖率和抽样覆盖建议。"
        )

        if not mapping_df.empty:
            filter_cols = st.columns([1.4, 1])
            selected_scenarios = filter_cols[0].multiselect(
                "审计场景",
                sorted(mapping_df["审计场景"].dropna().unique()),
                default=[],
                placeholder="全部场景",
            )
            unmatched_only = filter_cols[1].checkbox("只看待补充科目名称")
            filtered_mapping = mapping_df.copy()
            if selected_scenarios:
                filtered_mapping = filtered_mapping[filtered_mapping["审计场景"].isin(selected_scenarios)]
            if unmatched_only:
                filtered_mapping = filtered_mapping[filtered_mapping["匹配状态"] == "未匹配科目名称"]
            st.markdown("**配置映射预览**")
            st.dataframe(filtered_mapping, width="stretch", hide_index=True)

        with st.expander("技术明细：查看底层配置映射表", expanded=False):
            render_scenario_preview(ranked, show_amount=False)
        return

    st.markdown("### 审计价值 Dashboard")
    st.caption("从财务审计视角查看 SAP 自动分录对业务场景、公司和财务科目的影响；需要追溯时再展开底层配置与明细。")

    total_amount = float(dashboard_df["合计金额"].sum())
    scenario_count = int(dashboard_df["审计场景"].nunique())
    company_count = int(dashboard_df["公司代码"].nunique())
    account_count = int(dashboard_df["科目编码"].nunique())

    metric_cols = st.columns(4)
    metric_cols[0].metric("覆盖审计场景", f"{scenario_count}")
    metric_cols[1].metric("涉及公司", f"{company_count}")
    metric_cols[2].metric("命中科目", f"{account_count}")
    metric_cols[3].metric("归集金额", f"{total_amount:,.2f}")

    scenario_totals = (
        dashboard_df.groupby("审计场景", as_index=False)["合计金额"]
        .sum()
        .sort_values("合计金额", ascending=False)
    )
    top_scenario = scenario_totals.iloc[0]
    top_accounts = (
        dashboard_df.groupby(["审计场景", "科目编码", "科目描述"], as_index=False)["合计金额"]
        .sum()
        .sort_values("合计金额", ascending=False)
        .head(5)
    )
    concentrated_companies = (
        dashboard_df.groupby("公司代码", as_index=False)["合计金额"]
        .sum()
        .sort_values("合计金额", ascending=False)
        .head(3)
    )
    sample_focus = top_accounts.head(3).apply(
        lambda row: f"{row['审计场景']} - {row['科目编码']} {row['科目描述']}",
        axis=1,
    ).tolist()

    summary_lines = [
        f"金额影响最大的场景是 **{top_scenario['审计场景']}**，归集金额 **{float(top_scenario['合计金额']):,.2f}**。",
        f"金额贡献最高的科目是 **{top_accounts.iloc[0]['科目编码']} {top_accounts.iloc[0]['科目描述']}**，建议优先纳入样本覆盖。",
    ]
    if not concentrated_companies.empty:
        company_text = "、".join(f"{row['公司代码']}（{float(row['合计金额']):,.2f}）" for _, row in concentrated_companies.iterrows())
        summary_lines.append(f"自动分录金额较集中的公司包括：**{company_text}**，建议结合样本覆盖情况安排穿行测试。")
    if sample_focus:
        summary_lines.append("建议优先抽样对象：" + "；".join(sample_focus[:3]) + "。")

    st.markdown("**审计价值摘要**")
    st.info("\n\n".join(summary_lines))

    render_testing_coverage_dashboard(ranked)

    with st.expander("原始审计影响明细（可选）", expanded=False):
        filter_cols = st.columns([1.3, 1.3, 1])
        selected_scenarios = filter_cols[0].multiselect(
            "审计场景",
            sorted(dashboard_df["审计场景"].dropna().unique()),
            default=[],
            placeholder="全部场景",
            key="raw_detail_scenarios",
        )
        selected_companies = filter_cols[1].multiselect(
            "公司代码",
            sorted(dashboard_df["公司代码"].dropna().unique()),
            default=[],
            placeholder="全部公司",
            key="raw_detail_companies",
        )
        min_amount = filter_cols[2].number_input("金额阈值", min_value=0.0, value=0.0, step=10000.0, key="raw_detail_min_amount")

        filtered = dashboard_df.copy()
        if selected_scenarios:
            filtered = filtered[filtered["审计场景"].isin(selected_scenarios)]
        if selected_companies:
            filtered = filtered[filtered["公司代码"].isin(selected_companies)]
        if min_amount:
            filtered = filtered[filtered["合计金额"].abs() >= float(min_amount)]

        available_columns = [
            "流程分类", "审计场景", "子场景标签", "公司代码", "科目编码", "科目描述",
            "合计金额", "借方金额", "贷方金额",
        ]
        default_columns = ["审计场景", "子场景标签", "公司代码", "科目编码", "科目描述", "合计金额"]
        selected_columns = st.multiselect(
            "显示字段",
            available_columns,
            default=default_columns,
            key="raw_detail_columns",
        )
        if not selected_columns:
            selected_columns = default_columns

        display_df = filtered[selected_columns].copy()
        for amount_col in ["合计金额", "借方金额", "贷方金额"]:
            if amount_col in display_df.columns:
                display_df[amount_col] = display_df[amount_col].map(lambda value: f"{float(value):,.2f}")
        st.dataframe(display_df, width="stretch", hide_index=True)

    with st.expander("技术明细：配置映射、公司维度金额和借贷拆分", expanded=False):
        render_scenario_preview(ranked, show_amount=True)

def render_scenario_preview(ranked, show_amount=False):
    if not ranked:
        st.warning("尚未识别到场景，请检查 T030 配置表。")
        return

    preview_df = pd.DataFrame(ranked)
    preview_df["已匹配名称"] = preview_df["accounts"].apply(
        lambda items: sum("未知科目" not in str(item) for item in items)
    )
    preview_df["未匹配名称"] = preview_df["accounts"].apply(
        lambda items: sum("未知科目" in str(item) for item in items)
    )
    total_accounts = int(preview_df["已匹配名称"].sum() + preview_df["未匹配名称"].sum())
    matched_accounts = int(preview_df["已匹配名称"].sum())

    if show_amount:
        direction_filter = "全部"

        def account_chip(account, amount_value):
            return (
                "<span class='account-detail-chip'>"
                f"<span class='account-code'>{html.escape(str(account.get('account', '')))}</span>"
                f"<span class='account-desc'>{html.escape(str(account.get('description', '未知科目')))}</span>"
                f"<span class='account-amount'>{float(amount_value or 0):,.2f}</span>"
                "</span>"
            )

        def summary_breakdown_for_row(summary_row):
            scenario_name = str(summary_row.get("scenario", "")).strip()
            account_code = str(summary_row.get("account", "")).strip()
            company_amounts = {}

            for result in ranked:
                if str(result.get("name", "")).strip() != scenario_name:
                    continue
                for company in result.get("company_values", []) or []:
                    company_code = str(company.get("company_code", "未指定公司"))
                    for account in company.get("account_values", []) or []:
                        if str(account.get("account", "")).strip() != account_code:
                            continue
                        debit_value = amount_for_direction(account, "借方")
                        credit_value = amount_for_direction(account, "贷方")
                        combined_value = amount_for_direction(account, "全部")
                        if not (debit_value or credit_value or combined_value):
                            continue
                        company_amount = company_amounts.setdefault(company_code, {
                            "company_code": company_code,
                            "debit_value": 0.0,
                            "credit_value": 0.0,
                            "total_value": 0.0,
                        })
                        company_amount["debit_value"] += debit_value
                        company_amount["credit_value"] += credit_value
                        company_amount["total_value"] += combined_value

            if company_amounts:
                company_amount_list = sorted(
                    company_amounts.values(),
                    key=lambda item: (
                        -float(item.get("total_value", 0) or 0),
                        str(item.get("company_code", ""))
                    )
                )
                return {
                    "debit_value": sum(float(item.get("debit_value", 0) or 0) for item in company_amount_list),
                    "credit_value": sum(float(item.get("credit_value", 0) or 0) for item in company_amount_list),
                    "total_value": sum(float(item.get("total_value", 0) or 0) for item in company_amount_list),
                    "company_amounts": company_amount_list,
                }

            return {
                "debit_value": float(summary_row.get("debit_value", 0) or 0),
                "credit_value": float(summary_row.get("credit_value", 0) or 0),
                "total_value": float(summary_row.get("total_value", 0) or 0),
                "company_amounts": summary_row.get("company_amounts", []) or [],
            }

        company_codes = set()
        for result in ranked:
            for item in result.get("company_values", []):
                company_code = str(item.get("company_code", "未指定公司"))
                company_codes.add(company_code)
        company_codes = sorted(company_codes)

        if not company_codes:
            st.info("余额表最后期间未命中任何已关联场景科目，场景金额暂为 0。")
            return

        summary_rows = []
        for row in build_scenario_account_totals(ranked, direction_filter=direction_filter):
            company_codes_text = "、".join(str(code) for code in row.get("company_codes", []))
            subscenario_labels = subscenario_labels_for_summary_row(row, ranked)
            subscenario_html = label_chips_html(subscenario_labels)
            breakdown = summary_breakdown_for_row(row)
            company_amount_rows = []
            for company_amount in breakdown.get("company_amounts", []):
                company_amount_rows.append(
                    "<tr>"
                    f"<td>{html.escape(str(company_amount.get('company_code', '未指定公司')))}</td>"
                    f"<td class='amount'>{float(company_amount.get('debit_value', 0) or 0):,.2f}</td>"
                    f"<td class='amount'>{float(company_amount.get('credit_value', 0) or 0):,.2f}</td>"
                    f"<td class='amount'>{float(company_amount.get('total_value', 0) or 0):,.2f}</td>"
                    "</tr>"
                )
            company_amount_html = "".join(company_amount_rows) or (
                "<tr><td colspan='4' class='empty-cell'>暂无公司金额明细</td></tr>"
            )
            summary_rows.append(
                "<details class='summary-account-row'>"
                "<summary class='summary-row-grid'>"
                f"<span class='scenario-name'>{html.escape(str(row.get('scenario', '')))}</span>"
                f"<span class='subscenario-cell'>{subscenario_html}</span>"
                f"<span class='summary-account-code'>{html.escape(str(row.get('account', '')))}</span>"
                f"<span>{html.escape(str(row.get('description', '未知科目')))}</span>"
                f"<span class='amount'>{float(row.get('total_value', 0) or 0):,.2f}</span>"
                f"<span class='amount-share'>{float(row.get('amount_share_pct', 0) or 0):.2f}%</span>"
                f"<span class='summary-company-count' title='{html.escape(company_codes_text)}'>{int(row.get('company_count', 0) or 0)}</span>"
                "</summary>"
                "<div class='summary-side-panel'>"
                "<div class='side-metric-row'>"
                f"<span>借方金额 <strong>{float(breakdown.get('debit_value', 0) or 0):,.2f}</strong></span>"
                f"<span>贷方金额 <strong>{float(breakdown.get('credit_value', 0) or 0):,.2f}</strong></span>"
                f"<span>借贷合计 <strong>{float(breakdown.get('total_value', 0) or 0):,.2f}</strong></span>"
                "</div>"
                "<table class='summary-side-table'>"
                "<thead><tr><th>公司代码</th><th class='amount'>借方金额</th><th class='amount'>贷方金额</th><th class='amount'>合计金额</th></tr></thead>"
                f"<tbody>{company_amount_html}</tbody>"
                "</table>"
                "</div>"
                "</details>"
            )
        summary_html = ""
        if summary_rows:
            summary_html = (
                "<section class='scenario-total-summary'>"
                "<div class='summary-title'>场景科目总金额汇总 <span class='summary-subtitle'>点击科目行展开借贷明细</span></div>"
                "<div class='summary-row-grid summary-header'>"
                "<span>审计场景</span><span>子场景标签</span><span>科目编码</span><span>科目描述</span><span class='amount'>总金额</span><span class='amount-share'>占比</span><span>命中公司数</span>"
                "</div>"
                f"<div class='summary-accordion'>{''.join(summary_rows)}</div>"
                "</section>"
            )

        sections = []
        for idx, company_code in enumerate(company_codes):
            scenario_rows = []
            for result in ranked:
                company_item = next(
                    (item for item in result.get("company_values", []) if str(item.get("company_code", "未指定公司")) == company_code),
                    None
                )
                all_account_values = company_item.get("account_values", []) if company_item else []
                account_values = [
                    (account, amount_value)
                    for account in all_account_values
                    for amount_value in [amount_for_direction(account, direction_filter)]
                    if amount_value
                ]
                scenario_amount = sum(float(amount_value or 0) for _, amount_value in account_values)
                if account_values:
                    account_html = "".join(
                        account_chip(account, amount_value)
                        for account, amount_value in account_values
                    )
                else:
                    account_html = "<span class='empty-cell'>该公司最后期间未命中此场景科目</span>"
                scenario_rows.append(
                    "<tr>"
                    f"<td class='scenario-name'>{html.escape(str(result.get('name', '')))}</td>"
                    f"<td class='amount'>{scenario_amount:,.2f}</td>"
                    f"<td class='accounts-cell'>{account_html}</td>"
                    "</tr>"
                )
            sections.append(
                f"<details class='company-scenario-section' {'open' if idx == 0 else ''}>"
                "<summary>"
                f"<span>公司代码 {html.escape(company_code)}</span>"
                "</summary>"
                "<table class='company-scenario-table'>"
                "<thead><tr><th>审计场景</th><th class='amount'>场景金额</th><th>金额归集科目 / 科目描述 / 金额</th></tr></thead>"
                f"<tbody>{''.join(scenario_rows)}</tbody>"
                "</table>"
                "</details>"
            )

        legend_html = ""

        table_html = textwrap.dedent(f"""
            <style>
            .company-scenario-preview {{
                display: flex;
                flex-direction: column;
                gap: 12px;
            }}
            .company-scenario-section {{
                border: 1px solid #d8dde6;
                border-radius: 8px;
                background: #fff;
                overflow: hidden;
            }}
            .scenario-total-summary {{
                border: 1px solid #d8dde6;
                border-radius: 8px;
                background: #fff;
                overflow: hidden;
            }}
            .summary-title {{
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 12px 14px;
                background: #eef7f7;
                color: #00338d;
                font-weight: 800;
                border-bottom: 1px solid #d8dde6;
            }}
            .summary-subtitle {{
                color: #607085;
                font-size: 12px;
                font-weight: 600;
            }}
            .summary-row-grid {{
                display: grid;
                grid-template-columns: minmax(140px, .9fr) minmax(180px, 1.1fr) minmax(130px, .75fr) minmax(260px, 1.8fr) minmax(140px, .85fr) minmax(90px, .55fr) minmax(100px, .65fr);
                align-items: center;
                gap: 0;
                min-width: 1280px;
            }}
            .summary-header {{
                color: #4d5a6a;
                background: #fbfcfe;
                font-size: 14px;
                font-weight: 600;
                border-bottom: 1px solid #e7eaf0;
            }}
            .summary-header span,
            .summary-account-row summary span {{
                padding: 9px 12px;
                border-right: 1px solid #e7eaf0;
            }}
            .summary-header span:last-child,
            .summary-account-row summary span:last-child {{
                border-right: 0;
            }}
            .summary-accordion {{
                overflow-x: auto;
            }}
            .summary-account-row {{
                border-bottom: 1px solid #e7eaf0;
                font-size: 14px;
            }}
            .summary-account-row:last-child {{
                border-bottom: 0;
            }}
            .summary-account-row summary {{
                cursor: pointer;
                list-style: none;
                background: #fff;
                position: relative;
            }}
            .summary-account-row summary::-webkit-details-marker {{
                display: none;
            }}
            .summary-account-row summary:hover {{
                background: #f7fbff;
            }}
            .summary-account-row summary::before {{
                content: "▸";
                position: absolute;
                margin: 9px 0 0 2px;
                color: #00338d;
                font-weight: 800;
            }}
            .summary-account-row[open] summary::before {{
                content: "▾";
            }}
            .summary-account-row summary .scenario-name {{
                padding-left: 26px;
            }}
            .subscenario-cell {{
                display: flex;
                flex-wrap: wrap;
                gap: 5px;
                align-items: center;
            }}
            .subscenario-chip {{
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                padding: 3px 8px;
                background: #eef7f7;
                color: #005e5d;
                border: 1px solid #c9e7e6;
                font-size: 12px;
                font-weight: 700;
                line-height: 1.35;
                white-space: nowrap;
            }}
            .summary-side-panel {{
                background: #f8fbff;
                border-top: 1px solid #e7eaf0;
                padding: 12px 18px 14px 18px;
            }}
            .side-metric-row {{
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-bottom: 10px;
            }}
            .side-metric-row span {{
                border: 1px solid #d8dde6;
                border-radius: 999px;
                background: #fff;
                color: #4d5a6a;
                padding: 5px 10px;
            }}
            .side-metric-row strong {{
                color: #00338d;
                margin-left: 6px;
            }}
            .summary-side-table {{
                width: 100%;
                border-collapse: collapse;
                background: #fff;
                font-size: 13px;
            }}
            .summary-side-table th,
            .summary-side-table td {{
                border: 1px solid #e7eaf0;
                padding: 7px 9px;
                text-align: left;
            }}
            .summary-side-table th {{
                background: #fbfcfe;
                color: #4d5a6a;
                font-weight: 700;
            }}
            .summary-account-code {{
                color: #00338d;
                font-weight: 800;
                white-space: nowrap;
            }}
            .summary-company-count {{
                text-align: right;
                white-space: nowrap;
            }}
            .summary-row-grid .amount,
            .summary-row-grid .amount-share,
            .summary-side-table .amount {{
                text-align: right;
                white-space: nowrap;
            }}
            .company-scenario-section summary {{
                cursor: pointer;
                padding: 12px 14px;
                background: #f7f9fc;
                color: #00338d;
                font-weight: 700;
            }}
            .company-scenario-table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 14px;
            }}
            .company-scenario-table th,
            .company-scenario-table td {{
                border-top: 1px solid #e7eaf0;
                border-right: 1px solid #e7eaf0;
                padding: 10px 12px;
                text-align: left;
                vertical-align: top;
            }}
            .company-scenario-table th {{
                color: #4d5a6a;
                background: #fbfcfe;
                font-weight: 600;
            }}
            .company-scenario-table th:last-child,
            .company-scenario-table td:last-child {{
                border-right: 0;
            }}
            .company-scenario-table .scenario-name {{
                width: 14%;
                min-width: 110px;
                color: #1a1a1a;
                font-weight: 600;
            }}
            .company-scenario-table .amount {{
                width: 12%;
                min-width: 130px;
                text-align: right;
                white-space: nowrap;
            }}
            .company-scenario-table .accounts-cell {{
                white-space: normal;
                line-height: 1.9;
            }}
            .account-detail-chip {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                margin: 2px 6px 2px 0;
                padding: 2px 8px;
                max-width: 100%;
                border-radius: 999px;
                background: #f1f4f9;
                color: #53627a;
                flex-wrap: wrap;
            }}
            .account-detail-chip .account-code {{
                color: #00338d;
                font-weight: 700;
            }}
            .account-detail-chip .account-desc {{
                overflow-wrap: anywhere;
            }}
            .account-detail-chip .account-amount {{
                color: #006b6b;
                font-weight: 700;
                white-space: nowrap;
            }}
            .empty-cell {{
                color: #8a94a6;
            }}
            </style>
            <div class="company-scenario-preview">
                {legend_html}
                {summary_html}
                {''.join(sections)}
            </div>
            """).strip()
        st.html(table_html)
        if total_accounts and matched_accounts == 0:
            st.warning("当前 T030 场景科目没有在 SKAT 中找到对应名称；请确认上传的是完整 SKAT，或在下一步上传余额表补充科目名称。")
        return

    rows = []
    for _, row in preview_df.iterrows():
        detail_items = row.get("account_details", []) or []
        if detail_items:
            account_chips = "".join(
                "<span class='account-chip'>"
                f"<span class='account-code'>{html.escape(str(detail.get('account', '')))}</span>"
                f" ({html.escape(str(detail.get('description', '未知科目')))})"
                + "</span>"
                for detail in detail_items
            )
        else:
            account_chips = "".join(
                f"<span class='account-chip'>{html.escape(str(account))}</span>"
                for account in row.get("accounts", [])
            )
        account_chips = account_chips or "<span class='empty-cell'>无关联科目</span>"
        rows.append(
            "<tr>"
            f"<td class='scenario-name'>{html.escape(str(row.get('name', '')))}</td>"
            f"<td class='count-cell'>{int(row.get('已匹配名称', 0))}</td>"
            f"<td class='count-cell'>{int(row.get('未匹配名称', 0))}</td>"
            f"<td class='accounts-cell'>{account_chips}</td>"
            "</tr>"
        )

    table_html = textwrap.dedent(f"""
        <style>
        .scenario-preview-table {{
            width: 100%;
            border-collapse: collapse;
            background: #fff;
            border: 1px solid #d8dde6;
            border-radius: 8px;
            overflow: hidden;
            font-size: 14px;
        }}
        .scenario-preview-table th,
        .scenario-preview-table td {{
            border-bottom: 1px solid #e7eaf0;
            border-right: 1px solid #e7eaf0;
            padding: 10px 12px;
            text-align: left;
            vertical-align: top;
        }}
        .scenario-preview-table th {{
            background: #f7f9fc;
            color: #4d5a6a;
            font-weight: 600;
        }}
        .scenario-preview-table tr:last-child td {{
            border-bottom: 0;
        }}
        .scenario-preview-table th:last-child,
        .scenario-preview-table td:last-child {{
            border-right: 0;
        }}
        .scenario-preview-table .scenario-name {{
            width: 15%;
            min-width: 120px;
            color: #1a1a1a;
            font-weight: 600;
        }}
        .scenario-preview-table .amount {{
            width: 12%;
            min-width: 120px;
            text-align: right;
            white-space: nowrap;
        }}
        .scenario-preview-table .count-cell {{
            width: 8%;
            min-width: 82px;
            text-align: right;
            white-space: nowrap;
        }}
        .scenario-preview-table .accounts-cell {{
            width: auto;
            white-space: normal;
            line-height: 1.9;
        }}
        .scenario-preview-table .account-chip {{
            display: inline-block;
            margin: 2px 5px 2px 0;
            padding: 2px 8px;
            max-width: 100%;
            border-radius: 999px;
            background: #f1f4f9;
            color: #53627a;
            overflow-wrap: anywhere;
            white-space: normal;
        }}
        .scenario-preview-table .account-code {{
            color: #00338d;
            font-weight: 700;
        }}
        .scenario-preview-table .empty-cell {{
            color: #8a94a6;
        }}
        </style>
        <table class="scenario-preview-table">
            <thead>
                <tr>
                    <th>审计场景</th>
                    <th>已匹配名称</th>
                    <th>未匹配名称</th>
                    <th>关联科目</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """).strip()
    st.html(table_html)
    if total_accounts and matched_accounts == 0:
        st.warning("当前 T030 场景科目没有在 SKAT 中找到对应名称；请确认上传的是完整 SKAT，或在下一步上传余额表补充科目名称。")

recover_loaded_session_state()

# Main Header Area with Logo
logo_path = os.path.join(os.path.dirname(__file__), "kpmg_logo_official_white.png")
# Note: Since sidebar is removed, we'll use a blue header bar or just the logo
logo_b64 = get_base64_image(logo_path)

header_html = f"""
<div style="background-color: {KPMG_BLUE}; padding: 3rem 4rem; border-radius: 16px; margin: 0 0 2rem 0; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 8px 24px rgba(0,51,141,0.2);">
    <div style="display: flex; align-items: center;">
        <img src="data:image/png;base64,{logo_b64}" class="kpmg-header-logo">
        <div style="display: flex; flex-direction: column; justify-content: center;">
            <span class="kpmg-main-title">TSDA 测试范围框定辅助驾驶舱</span>
            <span class="kpmg-sub-title">面向财务审计与 IT 审计的自动过账、科目归集和样本证据分析工具</span>
        </div>
    </div>
    <div style="text-align: right; color: white;">
        <div style="font-size: 14px; font-weight: 600; letter-spacing: 1px;">SYSTEM ONLINE</div>
        <div style="font-size: 11px; opacity: 0.7; margin-top: 4px;">Session Tracking: {st.session_state.session_id[:12].upper()}</div>
        <div style="font-size: 10px; opacity: 0.65; margin-top: 4px;">Classifier {PROJECT_CLASSIFIER_VERSION}</div>
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# Model & Status Bar
c1, c2 = st.columns([3, 1], vertical_alignment="center")
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
    t1, t2, t3 = st.tabs(["📊 1. 审计影响总览", "📝 2. 样本证据叙述", "📥 3. 底稿成果下载"])
    with t1:
        st.subheader("SAP 自动分录对财务审计的影响")
        if res["ranked"]:
            render_general_audit_dashboard(res["ranked"])
            st.write("---")
            render_scenario_preview(res["ranked"], show_amount=True)
    with t2:
        st.subheader("TOD/TOE 样本证据描述")
        di_items = res.get("di", [])
        if di_items:
            for it in di_items:
                with st.expander(f"📌 {it['scenario']}"):
                    st.info(it["di_description"]); st.write("**样本细节记录 (TOE):**"); st.json(it["sample_table"])
        else:
            st.info("未生成 TOD/TOE 描述：当前样本没有命中任何场景关联科目。请检查 OCR 结果或样本清单中的凭证号、科目编码和金额字段。")
    with t3:
        st.subheader("最终成果文件导出")
        with open(res["report_path"], "rb") as f:
            st.download_button(label="📥 下载最终 Excel 审计底稿", data=f.read(), file_name=f"ITAC_WP_{st.session_state.audit_context.get('entity_name','Audit')}.xlsx", width="stretch")
        st.write("") 
        if st.button("🔄 开启新的审计任务", width="stretch"):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.current_step = 1
            st.session_state.results = None
            st.session_state.ocr_samples = []
            st.session_state.sample_table_records = []
            st.session_state.sample_table_signature = None
            st.session_state.sample_source_scenarios = {}
            st.session_state.processed_image_names = set()
            st.session_state.show_balloons = False
            st.session_state.base_files_ready = False
            st.session_state.base_file_signature = None
            st.session_state.trial_balance_ready = False
            st.session_state.trial_balance_signature = None
            st.session_state.t001k_ready = False
            st.session_state.t001k_signature = None
            st.session_state.mm03_image_names = []
            st.session_state.mm03_records = []
            st.session_state.mm03_signature = None
            st.session_state.project_folder_loaded = False
            st.session_state.project_folder_signature = None
            st.session_state.project_folder_manifest = []
            st.session_state.project_folder_summary = {}
            st.session_state.scenario_preview = []
            st.session_state.scenario_preview_schema_version = None
            st.rerun()
        st.write("---"); st.caption("© 2026 KPMG. All rights reserved. | IT Audit Technology & Innovation")
    st.stop()

# Progress
steps = ["📌 审计背景", "📊 自动分录映射", "📸 审计证据与分析"]
st.write(f"当前进度: **第 {st.session_state.current_step} 步 / 共 3 步** — {steps[st.session_state.current_step-1]}")
st.progress(st.session_state.current_step / 3.0)

# --- STEP 1 ---
if st.session_state.current_step == 1:
    st.subheader("步骤 1: 设置审计项目背景")
    st.markdown("**一键上传项目资料文件夹（推荐）**")
    st.caption("可直接选择项目文件夹，系统会自动识别并加载 T030、SKAT、全量序时账/凭证明细、余额/发生额表、T001K、样本清单、MM03 截图和凭证截图；后续步骤只需查看、筛选和必要时补充。")
    project_folder_files = st.file_uploader(
        "选择项目资料文件夹",
        type=["csv", "xlsx", "xls", "txt", "jpg", "jpeg", "png"],
        accept_multiple_files="directory",
        key="project_folder_uploader",
        label_visibility="collapsed",
    )
    render_project_folder_status()
    st.write("")
    with st.form("step1_form"):
        c1, c2 = st.columns(2)
        with c1:
            entity_name = st.text_input("被审计单位", placeholder="输入公司名称")
            saved_system_version = current_system_version()
            system_index = SYSTEM_VERSION_OPTIONS.index(saved_system_version) if saved_system_version in SYSTEM_VERSION_OPTIONS else 1
            system_name = st.selectbox("测试系统/版本", SYSTEM_VERSION_OPTIONS, index=system_index)
        with c2:
            period_start = st.date_input("审计起始日期", value=datetime.date(2026, 1, 1))
            period_end = st.date_input("审计截止日期", value=datetime.date(2026, 12, 31))
        st.write("")
        col_btn = st.columns([1, 1.5, 1])
        with col_btn[1]:
            if st.form_submit_button("下一步：识别自动分录映射", width="stretch"):
                if entity_name and system_name:
                    st.session_state.audit_context = {"entity_name": entity_name, "system_name": system_name, "system_version": system_name, "period_start": str(period_start), "period_end": str(period_end)}
                    if project_folder_files:
                        with st.spinner("正在自动识别项目资料包并加载可用清单..."):
                            summary = process_project_folder_upload(project_folder_files, selected_model)
                        if st.session_state.base_files_ready:
                            go_to_step(3)
                        else:
                            if summary.get("warnings"):
                                st.warning("；".join(summary["warnings"][:6]))
                            go_to_step(2)
                    else:
                        go_to_step(2)
                else: st.error("❗ 请完整填写背景信息。")

# --- STEP 2 ---
elif st.session_state.current_step == 2:
    st.subheader("步骤 2: 识别 SAP 自动分录与财务科目映射")
    st.caption("上传 SAP 自动过账配置与科目主数据，系统将识别收入、成本、存货、应付和生产等业务场景影响的财务科目。余额表可在下一步补充。")
    render_project_folder_status()
    t030_file = None
    skat_file = None
    if st.session_state.base_files_ready:
        st.success("T030/SKAT 已加载。需要替换时可展开下方区域重新上传。")
        with st.expander("替换自动过账配置与科目主数据", expanded=False):
            u1, u2 = st.columns(2)
            with u1: t030_file = st.file_uploader("自动过账配置（T030）", type=["csv", "xlsx", "xls"])
            with u2: skat_file = st.file_uploader("科目主数据（SKAT）", type=["csv", "xlsx", "xls"])
    else:
        u1, u2 = st.columns(2)
        with u1: t030_file = st.file_uploader("自动过账配置（T030）", type=["csv", "xlsx", "xls"])
        with u2: skat_file = st.file_uploader("科目主数据（SKAT）", type=["csv", "xlsx", "xls"])

    if t030_file and skat_file:
        base_signature = upload_signature(t030_file, skat_file)
        if base_signature != st.session_state.base_file_signature:
            with st.spinner("正在解析 T030/SKAT 并生成场景匹配预览..."):
                all_v = True
                for f_t, f_o in {"T030": t030_file, "SKAT": skat_file}.items():
                    is_v, msg = validate_upload_to_session(f_o, f_t)
                    if not is_v:
                        st.error(f"❌ {f_t} 失败: {msg}")
                        all_v = False
                        break
                if all_v:
                    tb_path = os.path.join(SESSION_DATA_DIR, "TrialBalance.csv")
                    if os.path.exists(tb_path):
                        os.remove(tb_path)
                    st.session_state.base_files_ready = True
                    st.session_state.base_file_signature = base_signature
                    st.session_state.trial_balance_ready = False
                    st.session_state.trial_balance_signature = None
                    refresh_scenario_preview()
                    st.success("已生成场景匹配预览。")
    elif st.session_state.base_files_ready:
        st.info("当前显示的是本会话已保存的 T030/SKAT 预览。")
    else:
        st.info("请先上传自动过账配置（T030）和科目主数据（SKAT）。")

    if st.session_state.base_files_ready:
        ensure_scenario_preview_current()
        st.write("**业务场景与财务科目映射预览**")
        render_scenario_preview(st.session_state.scenario_preview, show_amount=False)
        if any("未知科目" in str(acc) for row in st.session_state.scenario_preview for acc in row.get("accounts", [])):
            st.caption("提示：未知科目表示该科目未在当前 SKAT 中找到名称；后续上传余额表时可继续补充部分描述和金额。")

    st.write("---")
    nav_cols = st.columns([1, 1.5, 1.5, 1])
    with nav_cols[1]:
        if st.button("返回上一步", width="stretch"): go_to_step(1)
    with nav_cols[2]:
        if st.button("确认映射并进入审计分析", width="stretch", disabled=not st.session_state.base_files_ready):
            go_to_step(3)

# --- STEP 3 ---
elif st.session_state.current_step == 3:
    if not st.session_state.base_files_ready:
        st.warning("请先完成 T030/SKAT 场景匹配预览。")
        if st.button("返回上传配置表", width="stretch"):
            go_to_step(2)
        st.stop()

    st.subheader("步骤 3: 审计影响分析与样本证据采集")
    if is_s4_system():
        st.caption("SAP S/4 HANA：请上传手工整理过的编辑版科余表，或已按 ACDOCA 归集后的核对表；原始 ACDOCA 明细表过大时不建议直接上传。")
        tb_label = "可选：S/4 编辑版科目余额/发生额表或 ACDOCA 归集核对表（用于补充金额分析）"
    else:
        tb_label = "可选：科目余额/发生额表（用于补充金额分析和部分科目名称）"
    render_project_folder_status()
    ledger_files = []
    ledger_label = "推荐：全量序时账/凭证明细表（用于逐笔场景归类、配置验证与异常凭证清单）"
    if st.session_state.ledger_ready:
        st.success("全量序时账/凭证明细已加载。需要补充或替换时可展开下方区域。")
        with st.expander("补充或替换全量序时账/凭证明细", expanded=False):
            ledger_files = st.file_uploader(ledger_label, type=["csv", "xlsx", "xls", "txt"], accept_multiple_files=True)
    else:
        ledger_files = st.file_uploader(ledger_label, type=["csv", "xlsx", "xls", "txt"], accept_multiple_files=True)
    if ledger_files:
        ledger_signature = upload_signature(ledger_files)
        if ledger_signature != st.session_state.ledger_signature:
            with st.spinner("正在校验全量序时账并准备自动化凭证测试覆盖分析..."):
                is_v, msg, file_count = validate_uploads_to_session(ledger_files, "Ledger")
                if is_v:
                    st.session_state.ledger_ready = True
                    st.session_state.ledger_signature = ledger_signature
                    st.session_state.ledger_analysis_records = []
                    st.session_state.ledger_analysis_signature = None
                    st.success(f"已加载并合并 {file_count} 张全量序时账/凭证明细。")
                else:
                    st.error(f"❌ Ledger 失败: {msg}")
    elif st.session_state.ledger_ready:
        st.success("已加载本会话的全量序时账/凭证明细。")

    tb_files = []
    if st.session_state.trial_balance_ready:
        st.success("余额/发生额表已加载。需要补充或替换时可展开下方区域。")
        with st.expander("补充或替换余额/发生额表", expanded=False):
            tb_files = st.file_uploader(tb_label, type=["csv", "xlsx", "xls"], accept_multiple_files=True)
    else:
        tb_files = st.file_uploader(tb_label, type=["csv", "xlsx", "xls"], accept_multiple_files=True)
    if tb_files:
        tb_signature = upload_signature(tb_files)
        if tb_signature != st.session_state.trial_balance_signature:
            with st.spinner("正在校验余额表并刷新场景金额..."):
                is_v, msg, file_count = validate_uploads_to_session(tb_files, "TrialBalance")
                if is_v:
                    st.session_state.trial_balance_ready = True
                    st.session_state.trial_balance_signature = tb_signature
                    refresh_scenario_preview()
                    st.success(f"已加载并合并 {file_count} 张科目余额/发生额表，审计影响金额和可补充的科目名称已刷新。")
                else:
                    st.error(f"❌ TrialBalance 失败: {msg}")
    elif st.session_state.trial_balance_ready:
        st.success("已加载本会话的科目余额/发生额表。")
    else:
        st.info("可以先跳过金额表，直接上传样本或凭证截图生成底稿；审计影响金额将在上传金额表后显示。")

    ensure_scenario_preview_current()
    render_full_ledger_testing_dashboard(st.session_state.scenario_preview)
    render_account_quantity_coverage(st.session_state.scenario_preview)
    render_general_audit_dashboard(st.session_state.scenario_preview)

    st.write("---")
    with st.expander("技术补充与抽样场景表（可选）", expanded=False):
        st.markdown("**补充主数据并导出抽样场景表**")
        st.caption("补充公司代码与评估范围、物料主数据等 SAP 技术信息，用于把金额分析转换成可执行的样本覆盖范围。")
        master_cols = st.columns(2)
        with master_cols[0]:
            t001k_file = st.file_uploader("T001K 公司代码/评估分组代码表", type=["csv", "xlsx", "xls"])
        with master_cols[1]:
            mm03_images = st.file_uploader("MM03 物料主数据截图", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

        if t001k_file:
            t001k_signature = upload_signature(t001k_file)
            if t001k_signature != st.session_state.t001k_signature:
                is_v, msg = validate_upload_to_session(t001k_file, "T001K")
                if is_v:
                    st.session_state.t001k_ready = True
                    st.session_state.t001k_signature = t001k_signature
                    st.success("T001K 已加载，抽样场景表将补充评估分组代码。")
                else:
                    st.error(f"❌ T001K 失败: {msg}")
        elif st.session_state.t001k_ready:
            st.success("已加载本会话的 T001K。")

        if mm03_images:
            mm03_signature = upload_signature(mm03_images)
            if mm03_signature != st.session_state.mm03_signature:
                with st.status(f"正在解析 {len(mm03_images)} 张 MM03 截图...", expanded=False) as status:
                    ocr_engine = get_ocr_engine()
                    names = save_uploaded_images(mm03_images, "mm03")
                    records = []
                    for uploaded, saved_name in zip(mm03_images, names):
                        image_bytes = uploaded.getvalue()
                        parsed = ocr_engine.process_and_parse(image_bytes, llm_client=None)
                        if "error" in parsed:
                            record = parse_mm03_ocr_text("", saved_name)
                            record["ocr_status"] = parsed["error"]
                        else:
                            record = parse_mm03_ocr_text(parsed.get("OCR_TEXT", ""), saved_name)
                            record["ocr_status"] = "已解析"
                        records.append(record)
                    st.session_state.mm03_image_names = names
                    st.session_state.mm03_records = records
                    st.session_state.mm03_signature = mm03_signature
                    status.update(label=f"已解析 {len(records)} 张 MM03 截图", state="complete")
        pending_mm03_sources = st.session_state.get("project_pending_mm03_sources") or []
        if pending_mm03_sources:
            if not st.session_state.get("project_auto_mm03_attempted", False):
                st.session_state.project_auto_mm03_attempted = True
                with st.status(f"正在解析 {len(pending_mm03_sources)} 张 MM03 截图...", expanded=False) as status:
                    parsed_count, mm03_errors = process_pending_project_mm03_images()
                    if mm03_errors:
                        st.warning("；".join(mm03_errors[:5]))
                    status.update(label=f"已解析 {parsed_count} 张 MM03 截图", state="complete")
                pending_mm03_sources = st.session_state.get("project_pending_mm03_sources") or []
            if pending_mm03_sources:
                st.info(f"项目资料包中仍有 {len(pending_mm03_sources)} 张 MM03 截图待解析或待重试。")
                if st.button("重新解析项目资料包 MM03 截图", key="parse_project_mm03_images"):
                    with st.status(f"正在解析 {len(pending_mm03_sources)} 张 MM03 截图...", expanded=False) as status:
                        parsed_count, mm03_errors = process_pending_project_mm03_images()
                        if mm03_errors:
                            st.warning("；".join(mm03_errors[:5]))
                        status.update(label=f"已解析 {parsed_count} 张 MM03 截图", state="complete")
        if st.session_state.mm03_image_names:
            st.info(f"已记录 {len(st.session_state.mm03_image_names)} 张 MM03 截图，已解析 {len(st.session_state.mm03_records)} 张，将在抽样场景表中补充物料号、工厂编号与评估分类。")
        if st.session_state.mm03_records:
            with st.expander("预览 MM03 解析结果", expanded=False):
                st.dataframe(pd.DataFrame(mm03_records_to_dataframe_rows(st.session_state.mm03_records)), width="stretch")

        t001k_df = load_session_table("T001K")
        sampling_df = build_sampling_scenario_table(
            st.session_state.scenario_preview,
            t001k_df=t001k_df,
            mm03_image_names=st.session_state.mm03_image_names,
            mm03_records=st.session_state.mm03_records,
        )
        if sampling_df.empty:
            st.info("当前暂无可导出的抽样场景表，请先完成自动分录映射。")
        else:
            export_cols = st.columns([1.2, 2.8])
            with export_cols[0]:
                st.download_button(
                    "📥 导出抽样场景表",
                    data=dataframe_to_excel_bytes(sampling_df, "抽样场景表"),
                    file_name="Sampling_Scenario_Table.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch",
                )
            with export_cols[1]:
                st.caption("抽样场景表包含公司代码、评估分组、审计场景、科目、金额、占比，以及物料主数据补充信息。")
            with st.expander("预览抽样场景表", expanded=False):
                st.dataframe(sampling_df.head(50), width="stretch")

    st.write("---")
    sample_scenario_options = scenario_names_from_preview()
    if not sample_scenario_options:
        st.warning("请先完成场景匹配，系统需要已识别的审计场景后才能录入样本。")
        st.stop()
    st.caption("如同时上传采购、销售等不同场景的样本，请在上传后按文件分别选择对应审计场景。")
    samples_files = []
    voucher_images = []
    pending_voucher_sources = st.session_state.get("project_pending_voucher_sources") or []
    existing_project_samples = st.session_state.project_folder_loaded and (st.session_state.sample_table_records or st.session_state.ocr_samples or pending_voucher_sources)
    if existing_project_samples:
        st.success("样本清单/凭证截图已从第一步项目资料包自动加载。需要补充或替换时可展开下方区域。")
        with st.expander("补充样本清单或凭证截图", expanded=False):
            s1, s2 = st.columns(2)
            with s1: samples_files = st.file_uploader("方案 A: 样本清单", type=["csv", "xlsx", "xls"], accept_multiple_files=True)
            with s2: voucher_images = st.file_uploader("方案 B: 凭证截图", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    else:
        s1, s2 = st.columns(2)
        with s1: samples_files = st.file_uploader("方案 A: 样本清单", type=["csv", "xlsx", "xls"], accept_multiple_files=True)
        with s2: voucher_images = st.file_uploader("方案 B: 凭证截图", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    if pending_voucher_sources:
        if not st.session_state.get("project_auto_voucher_attempted", False) and not st.session_state.ocr_busy:
            st.session_state.project_auto_voucher_attempted = True
            st.session_state.ocr_busy = True
            try:
                with st.status(f"正在 OCR 解析 {len(pending_voucher_sources)} 张凭证截图...", expanded=False) as status:
                    added, voucher_errors = process_pending_project_voucher_images(selected_model)
                    if voucher_errors:
                        st.warning("；".join(voucher_errors[:5]))
                    status.update(label=f"已生成 {added} 行凭证样本", state="complete")
            finally:
                st.session_state.ocr_busy = False
            pending_voucher_sources = st.session_state.get("project_pending_voucher_sources") or []
        if pending_voucher_sources:
            if st.session_state.sample_table_records or st.session_state.ocr_samples:
                st.info(f"项目资料包中仍有 {len(pending_voucher_sources)} 张凭证截图待 OCR 或待重试；已加载的样本清单可直接生成底稿，截图仅作为补充证据。")
            else:
                st.info(f"项目资料包中仍有 {len(pending_voucher_sources)} 张凭证截图待 OCR 或待重试。")
            if st.button("重新解析项目资料包凭证截图", key="parse_project_voucher_images", disabled=st.session_state.ocr_busy):
                st.session_state.ocr_busy = True
                try:
                    with st.status(f"正在 OCR 解析 {len(pending_voucher_sources)} 张凭证截图...", expanded=False) as status:
                        added, voucher_errors = process_pending_project_voucher_images(selected_model)
                        if voucher_errors:
                            st.warning("；".join(voucher_errors[:5]))
                        status.update(label=f"已生成 {added} 行凭证样本", state="complete")
                finally:
                    st.session_state.ocr_busy = False
                st.rerun()
    if samples_files:
        samples_signature = upload_signature(samples_files)
        if samples_signature != st.session_state.sample_table_signature:
            account_descriptions = load_account_description_map(SESSION_DATA_DIR)
            table_records = []
            errors = []
            for uploaded in samples_files:
                is_v, msg, s_df = DataValidator.validate_file(uploaded, "Samples")
                if not is_v:
                    errors.append(f"{uploaded.name}: {msg}")
                    continue
                s_df.columns = [str(col).strip().upper() for col in s_df.columns]
                s_records = enrich_samples_with_account_descriptions(s_df.to_dict("records"), account_descriptions)
                s_records = normalize_sample_preview_records(s_records, source_type="样本清单", source_file=uploaded.name)
                s_records = apply_source_scenarios(s_records, st.session_state.sample_source_scenarios)
                table_records.extend(s_records)
            if errors:
                st.error("；".join(errors))
            else:
                st.session_state.sample_table_records = table_records
                st.session_state.ocr_samples, removed_ocr_samples = remove_duplicate_ocr_samples(
                    st.session_state.sample_table_records,
                    st.session_state.ocr_samples,
                )
                if removed_ocr_samples:
                    st.session_state.sample_dedupe_notice = (
                        f"已识别到 {len(removed_ocr_samples)} 行凭证截图 OCR 与样本清单凭证号重复；"
                        "系统保留样本清单作为主样本来源，截图不再重复纳入样本范围。"
                    )
                st.session_state.sample_table_signature = samples_signature
                st.session_state.ocr_samples_editor_nonce += 1
                st.success(f"已加载 {len(samples_files)} 个样本清单文件，共 {len(table_records)} 行样本。")
    elif st.session_state.sample_table_records:
        st.info(f"已加载本会话的样本清单，共 {len(st.session_state.sample_table_records)} 行。")

    if voucher_images:
        # Check if there are NEW images to process
        new_imgs = [img for img in voucher_images if img.name not in st.session_state.processed_image_names]
        if new_imgs:
            if "ocr_engine_inst" not in st.session_state:
                with st.status("🏗️ 初始化本地 OCR 引擎..."):
                    from ocr_processor import OCRProcessor
                    st.session_state.ocr_engine_inst = OCRProcessor()
            st.session_state.ocr_busy = True
            try:
                table_voucher_index = build_sample_voucher_index(st.session_state.sample_table_records)
                skipped_duplicate_rows = 0
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
                            account_descriptions = load_account_description_map(SESSION_DATA_DIR)
                            parsed_items = []
                            for it in res["items"]:
                                if it.get("DOC_NUM") and str(it.get("DOC_NUM")).lower() != "null":
                                    parsed_items.append(enrich_samples_with_account_descriptions([it], account_descriptions)[0])
                            parsed_items = normalize_sample_preview_records(parsed_items, source_type="凭证截图", source_file=img.name)
                            parsed_items = apply_source_scenarios(parsed_items, st.session_state.sample_source_scenarios)
                            for it in parsed_items:
                                if is_duplicate_voucher_sample(it, table_voucher_index):
                                    skipped_duplicate_rows += 1
                                    continue
                                item_id = f"{it.get('SOURCE_FILE')}_{it.get('DOC_NUM')}_{it.get('SAKNR')}_{it.get('AMOUNT')}_{it.get('DATE')}"
                                if item_id not in [f"{s.get('SOURCE_FILE')}_{s.get('DOC_NUM')}_{s.get('SAKNR')}_{s.get('AMOUNT')}_{s.get('DATE')}" for s in st.session_state.ocr_samples]:
                                    st.session_state.ocr_samples.append(it)
                            st.session_state.processed_image_names.add(img.name)
                        status.update(label=f"✅ {img.name} 完成", state="complete")
                if skipped_duplicate_rows:
                    st.session_state.sample_dedupe_notice = (
                        f"已识别到 {skipped_duplicate_rows} 行凭证截图 OCR 与样本清单凭证号重复；"
                        "系统保留样本清单作为主样本来源，截图不再重复纳入样本范围。"
                    )
            finally:
                st.session_state.ocr_busy = False
                st.rerun() # Refresh to enable button
    if st.session_state.get("sample_dedupe_notice"):
        st.info(st.session_state.sample_dedupe_notice)
    combined_sample_records = st.session_state.sample_table_records + st.session_state.ocr_samples
    if combined_sample_records:
        render_sample_source_scenario_controls(combined_sample_records, sample_scenario_options)
        combined_sample_records = st.session_state.sample_table_records + st.session_state.ocr_samples
        st.write("**📋 已录入样本预览**")
        preferred_columns = ["SOURCE_TYPE", "SOURCE_FILE", "SCENARIO", "DOC_NUM", "COMPANY_CODE", "DATE", "SAKNR", "TXT50", "MATNR", "AMOUNT", "SHKZG", "KTOSL", "KOMOK"]
        ocr_df = prepare_sample_editor_dataframe(
            combined_sample_records,
            sample_scenario_options,
            preferred_columns=preferred_columns,
        )
        edited_ocr_df = st.data_editor(
            ocr_df,
            width="stretch",
            num_rows="dynamic",
            key=f"ocr_samples_editor_{len(combined_sample_records)}_{st.session_state.ocr_samples_editor_nonce}",
            column_config={
                "SOURCE_TYPE": st.column_config.TextColumn("来源类型", disabled=True),
                "SOURCE_FILE": st.column_config.TextColumn("来源文件", disabled=True),
                "SCENARIO": st.column_config.SelectboxColumn("审计场景", options=sample_scenario_options, required=True),
                "DOC_NUM": st.column_config.TextColumn("DOC_NUM", required=True),
                "COMPANY_CODE": st.column_config.TextColumn("COMPANY_CODE"),
                "DATE": st.column_config.TextColumn("DATE"),
                "SAKNR": st.column_config.TextColumn("SAKNR", required=True),
                "TXT50": st.column_config.TextColumn("TXT50"),
                "MATNR": st.column_config.TextColumn("MATNR"),
                "AMOUNT": st.column_config.TextColumn("AMOUNT", required=True),
                "SHKZG": st.column_config.TextColumn("SHKZG"),
                "KTOSL": st.column_config.TextColumn("KTOSL"),
                "KOMOK": st.column_config.TextColumn("KOMOK"),
            },
        )
        edited_records = edited_ocr_df.fillna("").to_dict("records")
        st.session_state.sample_table_records, st.session_state.ocr_samples = split_sample_preview_records(edited_records)
        sync_source_scenarios_from_records(edited_records, sample_scenario_options)
        validation_df = validate_voucher_t030_logic(
            pd.DataFrame(edited_records),
            load_session_table("T030"),
            load_session_table("T001K"),
            st.session_state.mm03_records,
        )
        st.session_state.voucher_validation_records = validation_df.to_dict("records") if not validation_df.empty else []
        if not validation_df.empty:
            with st.expander("凭证到 T030 配置验证结果", expanded=True):
                st.caption("基于凭证公司代码、物料号、T001K 评估分组、MM03 评估分类和 T030 配置，判断样本科目是否按自动过账逻辑生成。")
                st.dataframe(validation_df, width="stretch", hide_index=True)
    st.write("---")
    nav_cols = st.columns([1, 1.5, 1.5, 1])
    with nav_cols[1]:
        if st.button("返回上一步", width="stretch"): go_to_step(2)
    with nav_cols[2]:
        final_sample_records = st.session_state.sample_table_records + st.session_state.ocr_samples
        has_ledger_analysis = bool(st.session_state.get("ledger_analysis_records"))
        btn_disabled = not final_sample_records and not has_ledger_analysis
        if st.session_state.ocr_busy and final_sample_records:
            st.caption("OCR 仍在处理补充截图；当前已有样本记录，可先生成底稿。")
        elif not final_sample_records and has_ledger_analysis:
            st.caption("已存在全量序时账分析，可先生成覆盖总览和异常凭证清单；样本凭证可后续补充生成 D&I 描述。")
        elif not final_sample_records:
            st.caption("请先上传样本清单、解析凭证截图，或上传全量序时账/凭证明细。")
        if st.button("🚀 生成最终底稿", width="stretch", disabled=btn_disabled):
            with st.spinner("AI 正在撰写穿行测试描述..."):
                c1 = Core1Orchestrator(SESSION_DATA_DIR); ranked = c1.run()
                invalid_rows = valid_sample_scenarios(final_sample_records, sample_scenario_options)
                if invalid_rows:
                    st.error(f"请为每条样本指定一个已识别审计场景；以下行未完成选择：{', '.join(map(str, invalid_rows[:20]))}")
                    st.stop()
                lines = []
                for s in final_sample_records:
                    lines.append({
                        "SCENARIO": s.get("SCENARIO"),
                        "DOC_NUM": s.get("DOC_NUM"),
                        "COMPANY_CODE": s.get("COMPANY_CODE"),
                        "SAKNR": s.get("SAKNR"),
                        "TXT50": s.get("TXT50"),
                        "MATNR": s.get("MATNR"),
                        "AMOUNT": s.get("AMOUNT"),
                        "SHKZG": s.get("SHKZG", "S"),
                        "DATE": s.get("DATE") or "2026-06-01",
                        "KTOSL": s.get("KTOSL"),
                        "KOMOK": s.get("KOMOK"),
                    })
                s_df = pd.DataFrame(lines)
                s_df = Core2Orchestrator.normalize_samples_dataframe(s_df)
                for col in ["SCENARIO", "DOC_NUM", "COMPANY_CODE", "SAKNR", "TXT50", "MATNR", "AMOUNT", "SHKZG", "DATE", "KTOSL", "KOMOK"]:
                    if col not in s_df.columns:
                        s_df[col] = ""
                if s_df["SCENARIO"].astype(str).str.strip().isin(["", AUTO_SCENARIO_LABEL]).any():
                    st.error("请为每条样本指定一个已识别审计场景。")
                    st.stop()
                s_df = s_df[["SCENARIO", "DOC_NUM", "COMPANY_CODE", "SAKNR", "TXT50", "MATNR", "AMOUNT", "SHKZG", "DATE", "KTOSL", "KOMOK"]]
                s_df.to_csv(os.path.join(SESSION_DATA_DIR, "Samples.csv"), index=False, encoding='utf-8-sig')
                validation_df = validate_voucher_t030_logic(
                    s_df,
                    load_session_table("T030"),
                    load_session_table("T001K"),
                    st.session_state.mm03_records,
                )
                st.session_state.voucher_validation_records = validation_df.to_dict("records") if not validation_df.empty else []
                
                # Debug: Show internal stats if results are weird
                if not ranked:
                    st.warning(f"⚠️ 核心引擎警告: 未能匹配到任何活跃的审计场景。请检查上传清单的内容。")
                elif not os.path.exists(os.path.join(SESSION_DATA_DIR, "TrialBalance.csv")):
                    st.info("未上传余额表，本次底稿的场景金额将暂按 0 展示。")
                elif sum(r['total_value'] for r in ranked) == 0:
                    st.warning("⚠️ 核心引擎警告: 余额表金额未能匹配到已识别场景，请检查余额表科目范围。")
                
                c2 = Core2Orchestrator(SESSION_DATA_DIR)
                # Use DEFAULT_KEY
                if DEFAULT_KEY:
                    from llm_client import LLMClient
                    c2.llm_client = LLMClient(api_key=DEFAULT_KEY, model_name=selected_model)
                
                audit_context = dict(st.session_state.audit_context)
                audit_context["voucher_validation"] = st.session_state.voucher_validation_records
                ledger_analysis_df = ensure_ledger_analysis_current(ranked)
                if not ledger_analysis_df.empty:
                    audit_context["full_ledger_summary"] = build_ledger_coverage_summary(ledger_analysis_df)
                    audit_context["full_ledger_exceptions"] = build_exception_ledger(ledger_analysis_df).to_dict("records")
                    audit_context["full_ledger_tagged"] = ledger_display_dataframe(ledger_analysis_df).to_dict("records")
                di = c2.generate_di_descriptions(ranked, audit_context)
                
                if not di:
                    st.info("💡 提示：未能从上传的凭证截图或 Samples 列表中找到与审计场景匹配的样本项目。")
                
                gen = ReportGenerator(SESSION_DATA_DIR); path = gen.generate(ranked, di, audit_context)
                st.session_state.results = {"ranked": ranked, "di": di, "report_path": path}
                st.session_state.show_balloons = True; st.rerun()

st.write("---")
st.caption("© 2026 KPMG. All rights reserved. | IT Audit Technology & Innovation")
