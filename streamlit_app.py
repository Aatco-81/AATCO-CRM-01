import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="AATCO CRM", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
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
    </style>
""", unsafe_allow_html=True)

# ── التحقق من تسجيل الدخول
if "user_info" not in st.session_state:
    st.session_state.user_info = None

if st.session_state.user_info is None:
    st.markdown("<h1 class='main-header'>🔐 نظام مبيعات AATCO</h1>", unsafe_allow_html=True)
    col_login, _, _ = st.columns([1.2, 0.4, 1])
    with col_login:
        with st.form("login_form"):
            user_input = st.text_input("👤 اسم المستخدم")
            pass_input = st.text_input("🔑 كلمة المرور", type="password")
            submitted  = st.form_submit_button("دخول للنظام")
        if submitted:
            try:
                conn     = st.connection("gsheets", type=GSheetsConnection)
                users_df = conn.read(worksheet="user_db", ttl=0)
                # تشخيص دقيق
                for _, row in users_df.iterrows():
                    st.write(f"صف: username={repr(row['username'])} password={repr(row['password'])}")
                st.write(f"مدخل: username={repr(str(user_input))} password={repr(str(pass_input))}")
                # مقارنة
                matched = False
                for _, row in users_df.iterrows():
                    if (str(row['username']).strip().lower() == str(user_input).strip().lower() and
                        str(row['password']).strip() == str(pass_input).strip()):
                        st.session_state.user_info = {
                            "full_name": str(row['full_name']).strip(),
                            "role":      str(row['role']).strip()
                        }
                        matched = True
                        break
                if matched:
                    st.rerun()
                else:
                    st.error("❌ بيانات الدخول غير صحيحة.")
            except Exception as e:
                st.error("⚠️ تعذّر الاتصال بقاعدة البيانات.")
                st.info(f"التفاصيل: {e}")
    st.stop()

# ── بعد تسجيل الدخول: توجيه للقائمة الجانبية
current_user = st.session_state.user_info['full_name']
current_role = st.session_state.user_info['role']

with st.sidebar:
    st.markdown(f"### 👤 {current_user}")
    st.caption(f"الصلاحية: {'مدير' if current_role == 'admin' else 'مندوب'}")
    st.divider()
    st.info("اختر صفحة من القائمة أعلاه")
    st.divider()
    if st.button("🚪 تسجيل الخروج"):
        st.session_state.user_info = None
        st.rerun()

st.markdown("<h2 class='main-header'>مرحباً بك في نظام AATCO CRM</h2>", unsafe_allow_html=True)
st.info("👈 اختر صفحة من القائمة الجانبية للبدء")
