import streamlit as st
import pandas as pd
import os
import datetime
import re
import base64
import time
import uuid
import html
import textwrap
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
if "scenario_preview" not in st.session_state: st.session_state.scenario_preview = []

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
    return tuple((f.name, getattr(f, "size", None)) for f in files if f is not None)

def validate_upload_to_session(uploaded_file, file_type):
    is_valid, msg, df = DataValidator.validate_file(uploaded_file, file_type)
    if is_valid:
        df.to_csv(os.path.join(SESSION_DATA_DIR, f"{file_type}.csv"), index=False, encoding="utf-8-sig")
    return is_valid, msg

def refresh_scenario_preview():
    ranked = Core1Orchestrator(SESSION_DATA_DIR).run()
    st.session_state.scenario_preview = ranked
    return ranked

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
        company_codes = set()
        for result in ranked:
            for item in result.get("company_values", []):
                company_code = str(item.get("company_code", "未指定公司"))
                company_codes.add(company_code)
        company_codes = sorted(company_codes)

        if not company_codes:
            st.info("余额表最后期间未命中任何已关联场景科目，场景金额暂为 0。")
            return

        sections = []
        for idx, company_code in enumerate(company_codes):
            scenario_rows = []
            for result in ranked:
                company_item = next(
                    (item for item in result.get("company_values", []) if str(item.get("company_code", "未指定公司")) == company_code),
                    None
                )
                scenario_amount = float(company_item.get("total_value", 0) or 0) if company_item else 0.0
                account_values = company_item.get("account_values", []) if company_item else []
                if account_values:
                    account_html = "".join(
                        "<span class='account-detail-chip'>"
                        f"<span class='account-code'>{html.escape(str(account.get('account', '')))}</span>"
                        f"<span class='account-desc'>{html.escape(str(account.get('description', '未知科目')))}</span>"
                        f"<span class='account-amount'>{float(account.get('total_value', 0) or 0):,.2f}</span>"
                        "</span>"
                        for account in account_values
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
                "<thead><tr><th>审计场景</th><th class='amount'>场景金额</th><th>关联科目 / 科目描述 / 金额</th></tr></thead>"
                f"<tbody>{''.join(scenario_rows)}</tbody>"
                "</table>"
                "</details>"
            )

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
                {''.join(sections)}
            </div>
            """).strip()
        st.html(table_html)
        if total_accounts and matched_accounts == 0:
            st.warning("当前 T030 场景科目没有在 SKAT 中找到对应名称；请确认上传的是完整 SKAT，或在下一步上传余额表补充科目名称。")
        return

    rows = []
    for _, row in preview_df.iterrows():
        account_chips = "".join(
            f"<span class='account-chip'>{html.escape(str(account))}</span>"
            for account in row.get("accounts", [])
        ) or "<span class='empty-cell'>无关联科目</span>"
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

# Main Header Area with Logo
logo_path = os.path.join(os.path.dirname(__file__), "kpmg_logo_official_white.png")
# Note: Since sidebar is removed, we'll use a blue header bar or just the logo
logo_b64 = get_base64_image(logo_path)

header_html = f"""
<div style="background-color: {KPMG_BLUE}; padding: 3rem 4rem; border-radius: 16px; margin: 0 0 2rem 0; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 8px 24px rgba(0,51,141,0.2);">
    <div style="display: flex; align-items: center;">
        <img src="data:image/png;base64,{logo_b64}" class="kpmg-header-logo">
        <div style="display: flex; flex-direction: column; justify-content: center;">
            <span class="kpmg-main-title">ITAC 自动化底稿生成中心</span>
            <span class="kpmg-sub-title">专业的 SAP 系统自动化控制测试辅助平台 | 毕马威IT Audit</span>
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
    t1, t2, t3 = st.tabs(["📊 1. 场景分析总览", "📝 2. AI 穿行测试叙述", "📥 3. 底稿成果下载"])
    with t1:
        st.subheader("识别场景与重要性排序")
        if res["ranked"]:
            render_scenario_preview(res["ranked"], show_amount=True)
    with t2:
        st.subheader("TOD/TOE 穿行测试描述")
        for it in res["di"]:
            with st.expander(f"📌 {it['scenario']}"):
                st.info(it["di_description"]); st.write("**样本细节记录 (TOE):**"); st.json(it["sample_table"])
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
            st.session_state.processed_image_names = set()
            st.session_state.show_balloons = False
            st.session_state.base_files_ready = False
            st.session_state.base_file_signature = None
            st.session_state.trial_balance_ready = False
            st.session_state.trial_balance_signature = None
            st.session_state.scenario_preview = []
            st.rerun()
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
            period_start = st.date_input("审计起始日期", value=datetime.date(2026, 1, 1))
            period_end = st.date_input("审计截止日期", value=datetime.date(2026, 12, 31))
        st.write("")
        col_btn = st.columns([1, 1.5, 1])
        with col_btn[1]:
            if st.form_submit_button("下一步：上传清单", width="stretch"):
                if entity_name and system_name:
                    st.session_state.audit_context = {"entity_name": entity_name, "system_name": system_name, "period_start": str(period_start), "period_end": str(period_end)}
                    st.session_state.current_step = 2; st.rerun()
                else: st.error("❗ 请完整填写背景信息。")

# --- STEP 2 ---
elif st.session_state.current_step == 2:
    st.subheader("步骤 2: 上传配置表并预览场景匹配")
    st.caption("先上传 T030 与 SKAT，即可查看各场景映射到的科目及当前可匹配到的科目名称。余额表可在下一步选择上传。")
    u1, u2 = st.columns(2)
    with u1: t030_file = st.file_uploader("T030 配置表", type=["csv", "xlsx", "xls"])
    with u2: skat_file = st.file_uploader("SKAT 科目表", type=["csv", "xlsx", "xls"])

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
        st.info("请先上传 T030 配置表和 SKAT 科目表。")

    if st.session_state.base_files_ready:
        st.write("**场景科目匹配预览**")
        render_scenario_preview(st.session_state.scenario_preview, show_amount=False)
        if any("未知科目" in str(acc) for row in st.session_state.scenario_preview for acc in row.get("accounts", [])):
            st.caption("提示：未知科目表示该科目未在当前 SKAT 中找到名称；后续上传余额表时可继续补充部分描述和金额。")

    st.write("---")
    nav_cols = st.columns([1, 1.5, 1.5, 1])
    with nav_cols[1]:
        if st.button("返回上一步", width="stretch"): st.session_state.current_step = 1; st.rerun()
    with nav_cols[2]:
        if st.button("确认场景匹配并下一步", width="stretch", disabled=not st.session_state.base_files_ready):
            st.session_state.current_step = 3; st.rerun()

# --- STEP 3 ---
elif st.session_state.current_step == 3:
    if not st.session_state.base_files_ready:
        st.warning("请先完成 T030/SKAT 场景匹配预览。")
        if st.button("返回上传配置表", width="stretch"):
            st.session_state.current_step = 2; st.rerun()
        st.stop()

    st.subheader("步骤 3: 补充余额表并采集审计样本证据")
    tb_file = st.file_uploader("可选：余额表（用于补充金额排序和部分科目名称）", type=["csv", "xlsx", "xls"])
    if tb_file:
        tb_signature = upload_signature(tb_file)
        if tb_signature != st.session_state.trial_balance_signature:
            with st.spinner("正在校验余额表并刷新场景金额..."):
                is_v, msg = validate_upload_to_session(tb_file, "TrialBalance")
                if is_v:
                    st.session_state.trial_balance_ready = True
                    st.session_state.trial_balance_signature = tb_signature
                    refresh_scenario_preview()
                    st.success("余额表已加载，场景金额和可补充的科目名称已刷新。")
                else:
                    st.error(f"❌ TrialBalance 失败: {msg}")
    elif st.session_state.trial_balance_ready:
        st.success("已加载本会话的余额表。")
    else:
        st.info("可以先跳过余额表，直接上传样本或凭证截图生成底稿；金额列将在上传余额表后显示。")

    with st.expander("查看当前场景匹配结果", expanded=not st.session_state.trial_balance_ready):
        render_scenario_preview(st.session_state.scenario_preview, show_amount=st.session_state.trial_balance_ready)

    st.write("---")
    s1, s2 = st.columns(2)
    with s1: samples_file = st.file_uploader("方案 A: 样本清单", type=["csv", "xlsx", "xls"])
    with s2: voucher_images = st.file_uploader("方案 B: 凭证截图", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
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
        st.dataframe(pd.DataFrame(st.session_state.ocr_samples), width="stretch")
    st.write("---")
    nav_cols = st.columns([1, 1.5, 1.5, 1])
    with nav_cols[1]:
        if st.button("返回上一步", width="stretch"): st.session_state.current_step = 2; st.rerun()
    with nav_cols[2]:
        # Only enable button if ocr is not busy AND we have either a file or OCR samples
        btn_disabled = st.session_state.ocr_busy or (not samples_file and not st.session_state.ocr_samples)
        if st.button("🚀 生成最终底稿", width="stretch", disabled=btn_disabled):
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
                
                di = c2.generate_di_descriptions(ranked, st.session_state.audit_context)
                
                if not di:
                    st.info("💡 提示：未能从上传的凭证截图或 Samples 列表中找到与审计场景匹配的样本项目。")
                
                gen = ReportGenerator(SESSION_DATA_DIR); path = gen.generate(ranked, di, st.session_state.audit_context)
                st.session_state.results = {"ranked": ranked, "di": di, "report_path": path}
                st.session_state.show_balloons = True; st.rerun()

st.write("---")
st.caption("© 2026 KPMG. All rights reserved. | IT Audit Technology & Innovation")
