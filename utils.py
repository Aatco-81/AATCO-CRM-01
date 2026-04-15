import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# ── الثوابت
REPS           = ["Hussam", "Khalil", "Ali", "Mohammed"]
SERVICE_TYPES  = ["صيانة", "تركيب", "تجديد", "تركيب قطع غيار"]
CUSTOMER_TYPES = ["مستشفى", "مدرسة", "فندق", "مطعم", "فردي", "مطور عقاري"]
STATUS_OPTIONS = [
    "جديدة",
    "تم تحديد موعد اجتماع",
    "تم إرسال عرض سعر",
    "مفاوضات",
    "تم التعاقد مع شركة أخرى",
    "لا يوجد مشاريع حالية لدى العميل",
    "مرفوض",
]
CLOSED_WON   = "تم التعاقد ✅"
CLOSED_LOST  = ["تم التعاقد مع شركة أخرى", "مرفوض", "لا يوجد مشاريع حالية لدى العميل"]
NEGLECT_DAYS = 7

APPT_TYPES   = ["اجتماع", "مكالمة", "زيارة ميدانية", "عرض تقديمي"]
APPT_STATUS  = ["قادم", "مكتمل", "ملغي"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; text-align: right; }
.stButton>button {
    width: 100%; border-radius: 8px;
    background-color: #1E3A8A; color: white;
    font-weight: bold; padding: 10px;
    transition: background-color 0.2s;
}
.stButton>button:hover { background-color: #2563EB; }
.main-header {
    color: #1E3A8A; text-align: center;
    padding: 12px; border-bottom: 2px solid #e2e8f0;
    margin-bottom: 20px;
}
[data-testid="stMetric"] {
    background-color: #f0f4ff;
    border: 1px solid #c7d7fc;
    border-radius: 12px;
    padding: 14px;
}
.contract-banner {
    background: #065F46; color: white;
    border-radius: 12px; padding: 20px 24px;
    text-align: center; margin: 16px 0;
    font-size: 18px; font-weight: bold;
}
.pending-banner {
    background: #FEF3C7; border: 1px solid #F59E0B;
    border-radius: 10px; padding: 14px 18px;
    color: #92400E; margin-bottom: 12px;
}
.step-header {
    background: #EFF6FF; border-right: 4px solid #1E3A8A;
    padding: 10px 14px; border-radius: 6px;
    font-weight: bold; color: #1E3A8A;
    margin-bottom: 14px;
}
[data-testid="stSidebar"] .stRadio > div { display: flex; flex-direction: column; gap: 12px; }
[data-testid="stSidebar"] .stRadio label { font-size: 16px !important; padding: 8px 4px !important; cursor: pointer; }
</style>
"""

def apply_css():
    st.markdown(CSS, unsafe_allow_html=True)

def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)

def read_sheet(worksheet):
    conn = get_conn()
    return conn.read(worksheet=worksheet, ttl=0)

def save_sheet(worksheet, data):
    conn = get_conn()
    conn.update(worksheet=worksheet, data=data)

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="data")
    return output.getvalue()

def require_login():
    """تحقق من تسجيل الدخول في كل صفحة"""
    if "user_info" not in st.session_state or st.session_state.user_info is None:
        st.warning("⚠️ يرجى تسجيل الدخول أولاً.")
        st.stop()
    return st.session_state.user_info

def sidebar_user():
    """عرض معلومات المستخدم في الشريط الجانبي"""
    user = require_login()
    with st.sidebar:
        st.markdown(f"### 👤 {user['full_name']}")
        st.caption(f"الصلاحية: {'مدير' if user['role'] == 'admin' else 'مندوب'}")
        st.divider()
        if st.button("🚪 تسجيل الخروج"):
            st.session_state.user_info = None
            st.rerun()
    return user
