import streamlit as st
import pandas as pd
from datetime import datetime, date, time
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import *

st.set_page_config(page_title="المواعيد", layout="wide")
apply_css()
user = sidebar_user()
current_user = user['full_name']
current_role = user['role']

st.markdown("<h2 class='main-header'>📅 جدول المواعيد</h2>", unsafe_allow_html=True)

try:
    df_appt = read_sheet("appointments")
    if 'status' not in df_appt.columns: df_appt['status'] = 'قادم'

    df_leads = read_sheet("leads_data")
    clients  = df_leads['client_name'].dropna().unique().tolist() if not df_leads.empty else []

    # ── إضافة موعد جديد
    with st.expander("➕ إضافة موعد جديد", expanded=False):
        with st.form("appt_form"):
            c1, c2 = st.columns(2)
            with c1:
                appt_client = st.selectbox("العميل", clients) if clients else st.text_input("اسم العميل")
                appt_type   = st.selectbox("نوع الموعد", APPT_TYPES)
                appt_rep    = st.selectbox("المندوب", REPS) if current_role == "admin" else current_user
            with c2:
                appt_date   = st.date_input("تاريخ الموعد", value=date.today())
                appt_time   = st.time_input("وقت الموعد",   value=time(9, 0))
                appt_status = st.selectbox("الحالة", APPT_STATUS)
            appt_notes = st.text_area("ملاحظات")
            save_appt  = st.form_submit_button("💾 حفظ الموعد")

        if save_appt:
            with st.spinner("جاري الحفظ..."):
                try:
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    new_appt = {
                        "id":               str(int(datetime.now().timestamp())),
                        "timestamp":        now_str,
                        "client_name":      str(appt_client),
                        "assigned_to":      appt_rep if current_role == "admin" else current_user,
                        "appointment_date": str(appt_date),
                        "appointment_time": str(appt_time),
                        "type":             appt_type,
                        "notes":            appt_notes,
                        "status":           appt_status,
                    }
                    updated = pd.concat([df_appt, pd.DataFrame([new_appt])], ignore_index=True)
                    save_sheet("appointments", updated)
                    st.success("✅ تم حفظ الموعد بنجاح.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")

    st.divider()

    # ── فلترة المواعيد
    if current_role == "admin":
        view_data = df_appt.copy()
    else:
        view_data = df_appt[df_appt['assigned_to'] == current_user].copy() if 'assigned_to' in df_appt.columns else df_appt.copy()

    if view_data.empty:
        st.info("لا توجد مواعيد مسجلة حالياً.")
        st.stop()

    # ── إحصاءات المواعيد
    m1, m2, m3 = st.columns(3)
    m1.metric("إجمالي المواعيد", len(view_data))
    m2.metric("📅 قادمة",        len(view_data[view_data.get('status', pd.Series()) == 'قادم'])  if 'status' in view_data.columns else 0)
    m3.metric("✅ مكتملة",       len(view_data[view_data.get('status', pd.Series()) == 'مكتمل']) if 'status' in view_data.columns else 0)

    st.divider()

    # ── فلاتر
    cf1, cf2 = st.columns(2)
    filter_status = cf1.selectbox("فلتر الحالة", ["الكل"] + APPT_STATUS)
    filter_type   = cf2.selectbox("فلتر النوع",  ["الكل"] + APPT_TYPES)

    filtered = view_data.copy()
    if filter_status != "الكل" and 'status' in filtered.columns:
        filtered = filtered[filtered['status'] == filter_status]
    if filter_type != "الكل" and 'type' in filtered.columns:
        filtered = filtered[filtered['type'] == filter_type]

    # ── جدول المواعيد
    st.subheader(f"📋 المواعيد ({len(filtered)})")
    show_cols = [c for c in ['appointment_date','appointment_time','client_name',
                              'assigned_to','type','status','notes']
                 if c in filtered.columns]

    # ترتيب حسب التاريخ
    if 'appointment_date' in filtered.columns:
        filtered = filtered.sort_values('appointment_date', ascending=True)

    st.dataframe(filtered[show_cols], use_container_width=True, height=400)

    # ── تحديث حالة موعد
    st.divider()
    with st.expander("✏️ تحديث حالة موعد"):
        if not view_data.empty and 'client_name' in view_data.columns:
            sel_client = st.selectbox("اختر العميل", view_data['client_name'].unique(), key="upd_client")
            sel_record = view_data[view_data['client_name'] == sel_client].iloc[0] if not view_data[view_data['client_name'] == sel_client].empty else None

            if sel_record is not None:
                with st.form("update_appt_form"):
                    new_appt_status = st.selectbox(
                        "الحالة الجديدة", APPT_STATUS,
                        index=APPT_STATUS.index(sel_record['status']) if sel_record['status'] in APPT_STATUS else 0
                    )
                    upd_notes = st.text_area("ملاحظات", value=str(sel_record.get('notes', '')))
                    upd_btn   = st.form_submit_button("💾 تحديث")

                if upd_btn:
                    with st.spinner("جاري التحديث..."):
                        try:
                            df_fresh = read_sheet("appointments")
                            idx = df_fresh[df_fresh['client_name'] == sel_client].index
                            df_fresh.loc[idx, 'status'] = new_appt_status
                            df_fresh.loc[idx, 'notes']  = upd_notes
                            save_sheet("appointments", df_fresh)
                            st.success("✅ تم التحديث.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ خطأ: {e}")

except Exception as e:
    st.error(f"❌ خطأ في تحميل البيانات: {e}")
