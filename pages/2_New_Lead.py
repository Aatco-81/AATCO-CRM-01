import streamlit as st
import pandas as pd
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import *

st.set_page_config(page_title="تسجيل فرصة", layout="wide")
apply_css()
user = sidebar_user()
current_user = user['full_name']
current_role = user['role']

st.markdown("<h2 class='main-header'>➕ تسجيل فرصة بيعية جديدة</h2>", unsafe_allow_html=True)

if "form_step" not in st.session_state:
    st.session_state.form_step = 1
if "form_data" not in st.session_state:
    st.session_state.form_data = {}

# ── الخطوة 1: بيانات العميل
if st.session_state.form_step == 1:
    st.markdown("<div class='step-header'>الخطوة 1 من 2 — بيانات العميل</div>", unsafe_allow_html=True)
    with st.form("step1_form"):
        c1, c2 = st.columns(2)
        with c1:
            client_name    = st.text_input("اسم العميل / المشروع *")
            customer_type  = st.selectbox("نوع العميل", CUSTOMER_TYPES)
            contact_person = st.text_input("الشخص المسؤول")
            position       = st.text_input("المنصب")
        with c2:
            phone        = st.text_input("رقم الجوال")
            location_url = st.text_input("رابط الموقع (Google Maps)")
            pref_time    = st.text_input("وقت التواصل المفضل")
            priority     = st.select_slider("درجة الأهمية", options=["محتمل", "مهم", "استراتيجي"])
        next_btn = st.form_submit_button("التالي ←")

    if next_btn:
        if not client_name.strip():
            st.warning("⚠️ يرجى إدخال اسم العميل.")
        else:
            st.session_state.form_data = {
                "client_name": client_name.strip(), "customer_type": customer_type,
                "contact_person": contact_person, "position": position,
                "phone": phone, "location_url": location_url,
                "pref_time": pref_time, "priority": priority,
            }
            st.session_state.form_step = 2
            st.rerun()

# ── الخطوة 2: تفاصيل الخدمة
elif st.session_state.form_step == 2:
    st.markdown("<div class='step-header'>الخطوة 2 من 2 — تفاصيل الخدمة</div>", unsafe_allow_html=True)
    st.info(f"العميل: **{st.session_state.form_data.get('client_name')}**")

    with st.form("step2_form"):
        c1, c2 = st.columns(2)
        with c1:
            service_type  = st.selectbox("نوع الخدمة", SERVICE_TYPES)
            num_elevators = st.number_input("عدد المصاعد", min_value=0, step=1, value=0)
        with c2:
            deal_value = st.number_input("💰 قيمة الصفقة المتوقعة (ريال)", min_value=0, step=500, value=0)
            assign_to  = st.selectbox("إسناد إلى", REPS) if current_role == "admin" else current_user
        notes = st.text_area("ملاحظات إضافية")
        cb, cs = st.columns(2)
        with cb: back_btn = st.form_submit_button("→ رجوع")
        with cs: save_btn = st.form_submit_button("💾 حفظ الفرصة")

    if back_btn:
        st.session_state.form_step = 1
        st.rerun()

    if save_btn:
        with st.spinner("جاري الحفظ..."):
            try:
                df_leads = read_sheet("leads_data")
                now_str  = datetime.now().strftime("%Y-%m-%d %H:%M")
                d        = st.session_state.form_data
                rep      = assign_to if current_role == "admin" else current_user
                new_row  = {
                    "id":             str(int(datetime.now().timestamp())),
                    "timestamp":      now_str,
                    "client_name":    d["client_name"],
                    "customer_type":  d["customer_type"],
                    "service_type":   service_type,
                    "num_elevators":  int(num_elevators),
                    "contact_person": d["contact_person"],
                    "position":       d["position"],
                    "phone":          d["phone"],
                    "pref_time":      d["pref_time"],
                    "location_url":   d["location_url"],
                    "priority":       d["priority"],
                    "deal_value":     int(deal_value),
                    "assigned_to":    rep,
                    "status":         "جديدة",
                    "notes":          notes,
                    "contracted":     "لا",
                    "contract_date":  "",
                    "last_update":    now_str,
                    "history":        f"[{now_str}] تسجيل جديد بواسطة {current_user}",
                }
                updated = pd.concat([df_leads, pd.DataFrame([new_row])], ignore_index=True)
                save_sheet("leads_data", updated)
                st.session_state.form_step = 1
                st.session_state.form_data = {}
                st.success(f"✅ تم تسجيل الفرصة وإسنادها لـ **{rep}**")
                st.balloons()
            except Exception as e:
                st.error(f"❌ خطأ أثناء الحفظ: {e}")
