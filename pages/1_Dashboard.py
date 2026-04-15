import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import *

st.set_page_config(page_title="لوحة التحكم", layout="wide")
apply_css()
user = sidebar_user()

if user['role'] != 'admin':
    st.error("❌ هذه الصفحة للمدير فقط.")
    st.stop()

st.markdown("<h2 class='main-header'>📊 لوحة تحكم فريق مبيعات AATCO</h2>", unsafe_allow_html=True)

try:
    df_all = read_sheet("leads_data")
    df_all = df_all.dropna(subset=['client_name'])
    df_all = df_all[df_all['client_name'].astype(str).str.strip() != '']

    if df_all.empty:
        st.info("قاعدة البيانات فارغة حالياً.")
        st.stop()

    if 'contracted'    not in df_all.columns: df_all['contracted']    = 'لا'
    if 'deal_value'    not in df_all.columns: df_all['deal_value']    = 0
    if 'contract_date' not in df_all.columns: df_all['contract_date'] = ''

    df_all['deal_value']  = pd.to_numeric(df_all['deal_value'],  errors='coerce').fillna(0)
    df_all['contracted']  = df_all['contracted'].astype(str).str.strip()

    contracted_df = df_all[df_all['contracted'] == 'نعم']
    active_df     = df_all[(df_all['contracted'] != 'نعم') & (~df_all['status'].isin(CLOSED_LOST))]

    # ── تنبيه الفرص المهملة
    if 'last_update' in df_all.columns:
        try:
            df_all['_lu'] = pd.to_datetime(df_all['last_update'], errors='coerce')
            threshold = datetime.now() - timedelta(days=NEGLECT_DAYS)
            neglected = df_all[
                (df_all['_lu'] < threshold) &
                (df_all['contracted'] != 'نعم') &
                (~df_all['status'].isin(CLOSED_LOST))
            ]
            if not neglected.empty:
                st.markdown(
                    f"<div class='pending-banner'>⏰ <b>{len(neglected)} فرصة</b> لم تُحدَّث منذ أكثر من {NEGLECT_DAYS} أيام</div>",
                    unsafe_allow_html=True
                )
        except Exception:
            pass

    # ── إحصاءات
    total     = len(df_all)
    n_cont    = len(contracted_df)
    n_active  = len(active_df)
    n_lost    = len(df_all[df_all['status'].isin(CLOSED_LOST)])
    conv_rate = f"{round(n_cont / total * 100)}%" if total else "0%"
    won_val   = contracted_df['deal_value'].sum()
    pipeline  = active_df['deal_value'].sum()

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("إجمالي الفرص",    total)
    m2.metric("✅ عقود مكتملة",  n_cont)
    m3.metric("🔄 تحت المتابعة", n_active)
    m4.metric("❌ خاسرة",        n_lost)
    m5.metric("📈 نسبة الإغلاق", conv_rate)
    m6.metric("💰 قيمة العقود",  f"{int(won_val):,} ﷼")

    st.divider()

    # ── رسوم بيانية
    c1, c2 = st.columns(2)
    with c1:
        rep_stats = df_all.groupby('assigned_to').apply(
            lambda x: pd.Series({
                'عقود مكتملة':  (x['contracted'] == 'نعم').sum(),
                'تحت المتابعة': ((x['contracted'] != 'نعم') & (~x['status'].isin(CLOSED_LOST))).sum(),
                'خاسرة':        x['status'].isin(CLOSED_LOST).sum(),
            })
        ).reset_index()
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(name='عقود مكتملة',  x=rep_stats['assigned_to'], y=rep_stats['عقود مكتملة'],  marker_color='#065F46'))
        fig1.add_trace(go.Bar(name='تحت المتابعة', x=rep_stats['assigned_to'], y=rep_stats['تحت المتابعة'], marker_color='#3B82F6'))
        fig1.add_trace(go.Bar(name='خاسرة',        x=rep_stats['assigned_to'], y=rep_stats['خاسرة'],        marker_color='#EF4444'))
        fig1.update_layout(title="أداء كل مندوب", barmode='group',
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Cairo"), height=320, legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        pie_data = pd.DataFrame({
            'الفئة': ['عقود مكتملة ✅', 'تحت المتابعة 🔄', 'خاسرة ❌'],
            'العدد': [n_cont, n_active, n_lost]
        })
        fig2 = px.pie(pie_data, values='العدد', names='الفئة', title="توزيع الفرص",
            color_discrete_map={'عقود مكتملة ✅':'#065F46','تحت المتابعة 🔄':'#3B82F6','خاسرة ❌':'#EF4444'})
        fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Cairo"), height=320)
        st.plotly_chart(fig2, use_container_width=True)

    # Pipeline المالي
    rep_pipeline = df_all.groupby('assigned_to').apply(
        lambda x: pd.Series({
            'قيمة العقود':   x[x['contracted'] == 'نعم']['deal_value'].sum(),
            'Pipeline نشط': x[(x['contracted'] != 'نعم') & (~x['status'].isin(CLOSED_LOST))]['deal_value'].sum(),
        })
    ).reset_index()
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(name='قيمة العقود',   x=rep_pipeline['assigned_to'], y=rep_pipeline['قيمة العقود'],   marker_color='#065F46'))
    fig3.add_trace(go.Bar(name='Pipeline نشط', x=rep_pipeline['assigned_to'], y=rep_pipeline['Pipeline نشط'], marker_color='#F59E0B'))
    fig3.update_layout(title="💰 Pipeline المالي (ريال)", barmode='stack',
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Cairo"), height=300, legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # ── فلاتر
    cf1, cf2, cf3, cf4 = st.columns(4)
    filter_rep      = cf1.selectbox("المندوب",     ["الكل"] + REPS)
    filter_status   = cf2.selectbox("الحالة",      ["الكل"] + STATUS_OPTIONS)
    filter_service  = cf3.selectbox("نوع الخدمة", ["الكل"] + SERVICE_TYPES)
    filter_contract = cf4.selectbox("حالة العقد",  ["الكل", "✅ عقود مكتملة", "⏳ لم يتم بعد"])
    search = st.text_input("🔍 بحث باسم العميل أو رقم الجوال")

    filtered = df_all.copy()
    if filter_rep      != "الكل": filtered = filtered[filtered['assigned_to'] == filter_rep]
    if filter_status   != "الكل": filtered = filtered[filtered['status']      == filter_status]
    if filter_service  != "الكل" and 'service_type' in filtered.columns:
        filtered = filtered[filtered['service_type'] == filter_service]
    if filter_contract == "✅ عقود مكتملة": filtered = filtered[filtered['contracted'] == 'نعم']
    if filter_contract == "⏳ لم يتم بعد":  filtered = filtered[filtered['contracted'] != 'نعم']
    if search:
        mask = (
            filtered['client_name'].astype(str).str.contains(search, case=False, na=False) |
            filtered['phone'].astype(str).str.contains(search, na=False)
        )
        filtered = filtered[mask]

    # ── إعادة الإسناد
    with st.expander("🔄 نقل / إعادة إسناد فرصة"):
        c_name  = st.selectbox("اختر العميل", df_all['client_name'].unique(), key="rc")
        new_rep = st.selectbox("إسناد إلى",   REPS, key="rr")
        if st.button("✅ تأكيد النقل"):
            with st.spinner("جاري النقل..."):
                try:
                    df_fresh = read_sheet("leads_data")
                    now_str  = datetime.now().strftime("%Y-%m-%d %H:%M")
                    df_fresh.loc[df_fresh['client_name'] == c_name, 'assigned_to'] = new_rep
                    df_fresh.loc[df_fresh['client_name'] == c_name, 'last_update'] = now_str
                    save_sheet("leads_data", df_fresh)
                    st.success(f"تم نقل **{c_name}** إلى **{new_rep}**")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")

    # ── جدول
    st.subheader(f"📋 الفرص ({len(filtered)})")
    show_cols = [c for c in ['timestamp','client_name','customer_type','service_type',
                              'num_elevators','phone','priority','deal_value',
                              'assigned_to','contracted','contract_date','status','last_update']
                 if c in filtered.columns]
    st.dataframe(filtered[show_cols], use_container_width=True, height=400)

    st.divider()
    excel_bytes = to_excel(filtered[show_cols])
    st.download_button(
        label="📤 تصدير إلى Excel",
        data=excel_bytes,
        file_name=f"AATCO_CRM_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

except Exception as e:
    st.error(f"❌ خطأ: {e}")
