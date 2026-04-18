import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import *

st.set_page_config(page_title="فرصي", layout="wide")
apply_css()
user = sidebar_user()
current_user = user['full_name']
current_role = user['role']

st.markdown(f"<h2 class='main-header'>🔄 فرصي — {current_user}</h2>", unsafe_allow_html=True)

try:
    df      = read_sheet("leads_data")
    # المدير يرى الكل، المندوب يرى فرصه فقط
    if current_role == "admin":
        my_data = df.copy()
    else:
        my_data = df[df['assigned_to'] == current_user].copy()

    if 'contracted'    not in my_data.columns: my_data['contracted']    = 'لا'
    if 'deal_value'    not in my_data.columns: my_data['deal_value']    = 0
    if 'contract_date' not in my_data.columns: my_data['contract_date'] = ''

    my_data['contracted'] = my_data['contracted'].astype(str).str.strip()

    if my_data.empty:
        st.info("ℹ️ لا توجد فرص مسندة إليك حالياً.")
        st.stop()

    # ── تنبيه الفرص المهملة
    if 'last_update' in my_data.columns:
        try:
            my_data['_lu'] = pd.to_datetime(my_data['last_update'], errors='coerce')
            threshold = datetime.now() - timedelta(days=NEGLECT_DAYS)
            neglected = my_data[
                (my_data['_lu'] < threshold) &
                (my_data['contracted'] != 'نعم') &
                (~my_data['status'].isin(CLOSED_LOST))
            ]
            if not neglected.empty:
                st.markdown(
                    f"<div class='pending-banner'>⏰ <b>{len(neglected)} فرصة</b> لم تُحدَّث منذ أكثر من {NEGLECT_DAYS} أيام</div>",
                    unsafe_allow_html=True
                )
        except Exception:
            pass

    # ── إحصاءات
    won_val = my_data[my_data['contracted'] == 'نعم']['deal_value'].apply(pd.to_numeric, errors='coerce').sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي الفرص",     len(my_data))
    c2.metric("✅ عقود مكتملة",   len(my_data[my_data['contracted'] == 'نعم']))
    c3.metric("🔄 تحت المتابعة",  len(my_data[(my_data['contracted'] != 'نعم') & (~my_data['status'].isin(CLOSED_LOST))]))
    c4.metric("💰 قيمة العقود",   f"{int(won_val):,} ﷼")

    st.divider()

    # ── بحث
    search = st.text_input("🔍 بحث باسم العميل أو رقم الجوال")
    display_data = my_data.copy()
    if search:
        mask = (
            display_data['client_name'].astype(str).str.contains(search, case=False, na=False) |
            display_data['phone'].astype(str).str.contains(search, na=False)
        )
        display_data = display_data[mask]

    clients = display_data['client_name'].unique() if not display_data.empty else my_data['client_name'].unique()
    if len(clients) == 0:
        st.info("لا توجد نتائج.")
        st.stop()

    target_client  = st.selectbox("اختر العميل", clients)
    current_record = my_data[my_data['client_name'] == target_client].iloc[0]
    is_contracted  = str(current_record.get('contracted', 'لا')).strip() == 'نعم'

    # ── بطاقة الحالة
    if is_contracted:
        contract_dt = current_record.get('contract_date', '')
        st.markdown(
            f"<div class='contract-banner'>🎉 تم التعاقد مع هذا العميل بنجاح!<br><small>{f'تاريخ العقد: {contract_dt}' if contract_dt else ''}</small></div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div class='pending-banner'>📋 الحالة: <b>{current_record['status']}</b> &nbsp;|&nbsp; الأولوية: <b>{current_record['priority']}</b> &nbsp;|&nbsp; العقد: <b>⏳ لم يتم بعد</b></div>",
            unsafe_allow_html=True
        )

    # ── فورم التحديث
    with st.form("update_form"):
        new_status   = st.selectbox(
            "تحديث حالة المتابعة", STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(current_record['status']) if current_record['status'] in STATUS_OPTIONS else 0
        )
        update_notes = st.text_area("آخر المستجدات", value=str(current_record.get('notes', '')))

        st.divider()
        st.markdown("#### 📝 تحويل الفرصة إلى عقد")

        if is_contracted:
            st.success("✅ هذه الفرصة تم تحويلها إلى عقد مسبقاً.")
            mark_contracted   = False
            unmark_contracted = st.checkbox("إلغاء تحويل العقد (يتطلب موافقة المدير)" if current_role != "admin" else "إلغاء تحويل العقد")
        else:
            st.warning("بعد التأكيد سيتم تسجيل الصفقة كعقد مكتمل.")
            mark_contracted   = st.checkbox("✅ تأكيد: تم التعاقد مع هذا العميل")
            unmark_contracted = False

        save_btn = st.form_submit_button("💾 حفظ التحديث")

    if save_btn:
        if unmark_contracted and current_role != "admin":
            st.error("❌ إلغاء العقد يتطلب صلاحية المدير.")
        else:
            with st.spinner("جاري الحفظ..."):
                try:
                    df_fresh = read_sheet("leads_data")
                    now_str  = datetime.now().strftime("%Y-%m-%d %H:%M")
                    idx      = df_fresh[df_fresh['client_name'] == target_client].index

                    # إضافة الأعمدة الناقصة وتحويلها لـ string
                    for col, default in [('contracted','لا'),('contract_date',''),('last_update',''),('history','')]:
                        if col not in df_fresh.columns:
                            df_fresh[col] = default
                        df_fresh[col] = df_fresh[col].fillna('').astype(str)

                    if mark_contracted:
                        new_contracted    = "نعم"
                        final_status      = CLOSED_WON
                        new_contract_date = now_str
                    elif unmark_contracted:
                        new_contracted    = "لا"
                        final_status      = new_status
                        new_contract_date = ""
                    else:
                        new_contracted    = str(current_record.get('contracted', 'لا'))
                        final_status      = new_status
                        new_contract_date = str(current_record.get('contract_date', ''))

                    old_hist     = str(df_fresh.loc[idx[0], 'history']) if len(idx) > 0 else ""
                    if old_hist in ['nan', 'None', '']: old_hist = ""
                    contract_tag = " — تم التعاقد 🎉" if mark_contracted else ""
                    new_hist     = f"{old_hist}\n[{now_str}] {current_user}: {final_status}{contract_tag} — {update_notes}".strip()

                    df_fresh.loc[idx, 'status']        = final_status
                    df_fresh.loc[idx, 'contracted']    = new_contracted
                    df_fresh.loc[idx, 'contract_date'] = new_contract_date
                    df_fresh.loc[idx, 'notes']         = update_notes
                    df_fresh.loc[idx, 'last_update']   = now_str
                    df_fresh.loc[idx, 'history']       = new_hist

                    save_sheet("leads_data", df_fresh)

                    if mark_contracted:
                        st.success(f"🎉 تهانينا! تم تحويل **{target_client}** إلى عقد!")
                        st.balloons()
                    else:
                        st.success(f"✅ تم تحديث **{target_client}** بنجاح.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ في التحديث: {e}")

    # ── سجل التحديثات
    if 'history' in my_data.columns:
        hist_val = str(current_record.get('history', ''))
        if hist_val.strip():
            with st.expander("📝 سجل تاريخ التحديثات"):
                for line in reversed(hist_val.strip().split('\n')):
                    if line.strip():
                        st.markdown(f"- {line.strip()}")

    # ── جدول الفرص
    st.divider()
    st.subheader("📋 جميع الفرص")
    show_cols = [c for c in ['client_name','customer_type','service_type','num_elevators',
                              'phone','priority','deal_value','contracted','contract_date','status','last_update']
                 if c in my_data.columns]
    st.dataframe(my_data[show_cols], use_container_width=True)

except Exception as e:
    st.error(f"❌ خطأ في تحميل البيانات: {e}")
