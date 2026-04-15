import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import *

st.set_page_config(page_title="التقارير", layout="wide")
apply_css()
user = sidebar_user()
current_role = user['role']

if current_role != 'admin':
    st.error("❌ هذه الصفحة للمدير فقط.")
    st.stop()

st.markdown("<h2 class='main-header'>📈 التقارير المتقدمة</h2>", unsafe_allow_html=True)

try:
    df = read_sheet("leads_data")
    df = df.dropna(subset=['client_name'])
    df = df[df['client_name'].astype(str).str.strip() != '']

    if df.empty:
        st.info("لا توجد بيانات كافية للتقارير.")
        st.stop()

    # ── تجهيز البيانات
    if 'contracted'    not in df.columns: df['contracted']    = 'لا'
    if 'deal_value'    not in df.columns: df['deal_value']    = 0
    if 'contract_date' not in df.columns: df['contract_date'] = ''
    if 'timestamp'     not in df.columns: df['timestamp']     = ''

    df['deal_value']   = pd.to_numeric(df['deal_value'], errors='coerce').fillna(0)
    df['contracted']   = df['contracted'].astype(str).str.strip()
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['contract_dt']  = pd.to_datetime(df['contract_date'], errors='coerce')
    df['month']        = df['timestamp_dt'].dt.to_period('M').astype(str)
    df['month_label']  = df['timestamp_dt'].dt.strftime('%Y-%m')

    contracted_df = df[df['contracted'] == 'نعم']
    total         = len(df)
    n_cont        = len(contracted_df)

    # ════════════════════════════
    # 1. معدل التحويل
    # ════════════════════════════
    st.subheader("📊 معدل التحويل (Conversion Rate)")

    conv_overall = round(n_cont / total * 100, 1) if total else 0

    cm1, cm2, cm3 = st.columns(3)
    cm1.metric("إجمالي الفرص",      total)
    cm2.metric("عقود مكتملة",       n_cont)
    cm3.metric("معدل التحويل الكلي", f"{conv_overall}%")

    # معدل التحويل لكل مندوب
    rep_conv = df.groupby('assigned_to').apply(
        lambda x: pd.Series({
            'إجمالي الفرص': len(x),
            'عقود مكتملة':  (x['contracted'] == 'نعم').sum(),
            'معدل التحويل': f"{round((x['contracted'] == 'نعم').sum() / len(x) * 100, 1)}%" if len(x) > 0 else "0%"
        })
    ).reset_index()

    st.dataframe(rep_conv, use_container_width=True)

    # رسم بياني
    rep_conv['نسبة التحويل'] = rep_conv['عقود مكتملة'] / rep_conv['إجمالي الفرص'] * 100
    fig_conv = px.bar(
        rep_conv, x='assigned_to', y='نسبة التحويل',
        title="معدل التحويل لكل مندوب (%)",
        color='نسبة التحويل',
        color_continuous_scale=['#EF4444', '#F59E0B', '#065F46'],
        text=rep_conv['نسبة التحويل'].round(1).astype(str) + '%'
    )
    fig_conv.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Cairo"), height=350, showlegend=False
    )
    fig_conv.update_traces(textposition='outside')
    st.plotly_chart(fig_conv, use_container_width=True)

    st.divider()

    # ════════════════════════════
    # 2. متوسط دورة البيع
    # ════════════════════════════
    st.subheader("⏱️ متوسط دورة البيع (Sales Cycle)")

    cycle_df = contracted_df[
        contracted_df['timestamp_dt'].notna() &
        contracted_df['contract_dt'].notna()
    ].copy()

    if not cycle_df.empty:
        cycle_df['cycle_days'] = (cycle_df['contract_dt'] - cycle_df['timestamp_dt']).dt.days
        cycle_df = cycle_df[cycle_df['cycle_days'] >= 0]

        avg_cycle = round(cycle_df['cycle_days'].mean(), 1) if not cycle_df.empty else 0
        min_cycle = int(cycle_df['cycle_days'].min()) if not cycle_df.empty else 0
        max_cycle = int(cycle_df['cycle_days'].max()) if not cycle_df.empty else 0

        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("متوسط دورة البيع", f"{avg_cycle} يوم")
        sc2.metric("أسرع صفقة",        f"{min_cycle} يوم")
        sc3.metric("أطول صفقة",        f"{max_cycle} يوم")

        # متوسط دورة البيع لكل مندوب
        rep_cycle = cycle_df.groupby('assigned_to')['cycle_days'].mean().round(1).reset_index()
        rep_cycle.columns = ['المندوب', 'متوسط الأيام']

        fig_cycle = px.bar(
            rep_cycle, x='المندوب', y='متوسط الأيام',
            title="متوسط دورة البيع لكل مندوب (أيام)",
            color='متوسط الأيام',
            color_continuous_scale=['#065F46', '#F59E0B', '#EF4444'],
            text=rep_cycle['متوسط الأيام'].astype(str) + ' يوم'
        )
        fig_cycle.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Cairo"), height=350, showlegend=False
        )
        fig_cycle.update_traces(textposition='outside')
        st.plotly_chart(fig_cycle, use_container_width=True)
    else:
        st.info("⚠️ لا توجد بيانات كافية لحساب دورة البيع. تأكد من تسجيل تواريخ التعاقد.")

    st.divider()

    # ════════════════════════════
    # 3. الأداء الشهري
    # ════════════════════════════
    st.subheader("📅 الأداء الشهري")

    if df['timestamp_dt'].notna().any():
        monthly = df.groupby('month_label').apply(
            lambda x: pd.Series({
                'فرص جديدة':     len(x),
                'عقود مكتملة':   (x['contracted'] == 'نعم').sum(),
                'قيمة العقود':   x[x['contracted'] == 'نعم']['deal_value'].sum(),
            })
        ).reset_index().sort_values('month_label')

        # رسم مزدوج: فرص + عقود
        fig_monthly = go.Figure()
        fig_monthly.add_trace(go.Bar(
            name='فرص جديدة', x=monthly['month_label'], y=monthly['فرص جديدة'],
            marker_color='#3B82F6', opacity=0.8
        ))
        fig_monthly.add_trace(go.Bar(
            name='عقود مكتملة', x=monthly['month_label'], y=monthly['عقود مكتملة'],
            marker_color='#065F46'
        ))
        fig_monthly.update_layout(
            title="الفرص والعقود شهرياً", barmode='group',
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Cairo"), height=350,
            legend=dict(orientation="h", y=-0.2)
        )
        st.plotly_chart(fig_monthly, use_container_width=True)

        # رسم القيمة المالية الشهرية
        fig_val = px.line(
            monthly, x='month_label', y='قيمة العقود',
            title="💰 قيمة العقود المكتملة شهرياً (ريال)",
            markers=True,
            color_discrete_sequence=['#065F46']
        )
        fig_val.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Cairo"), height=320
        )
        st.plotly_chart(fig_val, use_container_width=True)

        # جدول ملخص شهري
        st.subheader("📋 ملخص شهري")
        monthly['قيمة العقود'] = monthly['قيمة العقود'].apply(lambda x: f"{int(x):,} ﷼")
        monthly['معدل التحويل'] = monthly.apply(
            lambda r: f"{round(r['عقود مكتملة'] / r['فرص جديدة'] * 100, 1)}%" if r['فرص جديدة'] > 0 else "0%",
            axis=1
        )
        monthly.rename(columns={'month_label': 'الشهر'}, inplace=True)
        st.dataframe(monthly[['الشهر','فرص جديدة','عقود مكتملة','معدل التحويل','قيمة العقود']], use_container_width=True)
    else:
        st.info("لا توجد بيانات شهرية كافية.")

    st.divider()

    # ── تصدير التقرير
    excel_bytes = to_excel(df[[c for c in ['timestamp','client_name','assigned_to','service_type',
                                            'deal_value','contracted','contract_date','status']
                                if c in df.columns]])
    st.download_button(
        label="📤 تصدير التقرير الكامل إلى Excel",
        data=excel_bytes,
        file_name=f"AATCO_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

except Exception as e:
    st.error(f"❌ خطأ في تحميل البيانات: {e}")
