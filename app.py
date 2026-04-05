"""
Marketing Attribution Intelligence Platform
B2C Subscription Brand — Full Lifecycle Analytics
Simulates: GA4 · HubSpot · Meta Ads · Google Ads · Klaviyo · Segment · Mixpanel
"""
import sqlite3, os, json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import os
DB = os.path.join(os.path.dirname(__file__), "marketing_attribution.db")

st.set_page_config(
    page_title="Marketing Attribution Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
[data-testid="stMetricValue"]{font-size:1.6rem;font-weight:600}
.platform-badge{display:inline-block;padding:2px 10px;border-radius:12px;
  font-size:11px;font-weight:600;margin:2px}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def q(sql, params=()):
    return pd.read_sql_query(sql, get_conn(), params=params)

PLATFORM_COLORS = {
    "GA4":"#E37400","Meta Ads":"#1877F2","Google Ads":"#4285F4",
    "Klaviyo":"#22BC66","Mixpanel":"#7856FF","HubSpot":"#FF7A59","Segment":"#52BD94"
}

PAGES = ["📊 Attribution Models","💰 Spend & ROI","🔄 Full Funnel",
         "💎 LTV & Retention","🛒 Cart & Reactivation","📣 Brand & Share of Voice",
         "🗄️ Data Sources"]

with st.sidebar:
    st.title("📊 Attribution Platform")
    st.caption("B2C Subscription Brand · Full Lifecycle")
    page = st.radio("Navigation", PAGES, label_visibility="collapsed")
    st.divider()
    st.caption("**Simulated Data Sources**")
    for p,col in PLATFORM_COLORS.items():
        st.markdown(f'<span class="platform-badge" style="background:{col}20;color:{col};border:1px solid {col}40">{p}</span>',
                    unsafe_allow_html=True)
    st.divider()
    date_range = st.date_input("Date Range",
        value=[pd.to_datetime("2023-01-01"), pd.to_datetime("2024-12-31")],
        min_value=pd.to_datetime("2023-01-01"),
        max_value=pd.to_datetime("2024-12-31"))
    start_d = str(date_range[0]) if len(date_range)==2 else "2023-01-01"
    end_d   = str(date_range[1]) if len(date_range)==2 else "2024-12-31"

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — ATTRIBUTION MODELS
# ══════════════════════════════════════════════════════════════════════════════
if page == PAGES[0]:
    st.title("Multi-Touch Attribution Models")
    st.caption("Comparing First Touch · Last Touch · Linear · Time Decay · U-Shaped across all channels")

    model_df = q("""
        SELECT ch.channel_name, ch.source_platform,
               ROUND(SUM(fa.credit_first_touch * fa.conversion_revenue),2) as first_touch,
               ROUND(SUM(fa.credit_last_touch  * fa.conversion_revenue),2) as last_touch,
               ROUND(SUM(fa.credit_linear      * fa.conversion_revenue),2) as linear,
               ROUND(SUM(fa.credit_time_decay  * fa.conversion_revenue),2) as time_decay,
               ROUND(SUM(fa.credit_u_shaped    * fa.conversion_revenue),2) as u_shaped,
               COUNT(DISTINCT fa.conversion_id) as conversions
        FROM fact_attribution fa
        JOIN dim_channel ch ON fa.channel_id = ch.channel_id
        JOIN fact_conversions fc ON fa.conversion_id = fc.conversion_id
        WHERE fc.conversion_date BETWEEN ? AND ?
        GROUP BY ch.channel_name, ch.source_platform
        ORDER BY linear DESC
    """, (start_d, end_d))

    col1,col2,col3,col4,col5 = st.columns(5)
    total = model_df["linear"].sum()
    col1.metric("Total Attributed Revenue", f"${total:,.0f}")
    col2.metric("Channels", len(model_df))
    col3.metric("Conversions", f"{model_df['conversions'].sum():,}")
    top = model_df.iloc[0]["channel_name"] if len(model_df) else "—"
    col4.metric("Top Channel (Linear)", top)
    spread = model_df["first_touch"].max() - model_df["last_touch"].min() if len(model_df) else 0
    col5.metric("Model Variance", f"${spread:,.0f}")

    st.divider()

    model_choice = st.selectbox("Compare attribution models",
        ["All Models Side by Side","First Touch vs Last Touch","Linear vs U-Shaped","Time Decay Detail"])

    if model_choice == "All Models Side by Side":
        melt = model_df.melt(id_vars=["channel_name"],
            value_vars=["first_touch","last_touch","linear","time_decay","u_shaped"],
            var_name="Model", value_name="Revenue")
        fig = px.bar(melt, x="channel_name", y="Revenue", color="Model", barmode="group",
                     title="Attributed Revenue by Channel — All Models",
                     labels={"channel_name":"Channel","Revenue":"Attributed Revenue ($)"})
        st.plotly_chart(fig, use_container_width=True)

    elif model_choice == "First Touch vs Last Touch":
        fig = go.Figure()
        fig.add_trace(go.Bar(name="First Touch", x=model_df["channel_name"], y=model_df["first_touch"]))
        fig.add_trace(go.Bar(name="Last Touch",  x=model_df["channel_name"], y=model_df["last_touch"]))
        fig.update_layout(barmode="group", title="First Touch vs Last Touch Attribution",
                          xaxis_title="Channel", yaxis_title="Attributed Revenue ($)")
        st.plotly_chart(fig, use_container_width=True)
        st.info("**Insight:** Channels with high First Touch but low Last Touch credit are strong awareness drivers. Channels strong on Last Touch are closers.")

    elif model_choice == "Linear vs U-Shaped":
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Linear",   x=model_df["channel_name"], y=model_df["linear"]))
        fig.add_trace(go.Bar(name="U-Shaped", x=model_df["channel_name"], y=model_df["u_shaped"]))
        fig.update_layout(barmode="group", title="Linear vs U-Shaped Attribution")
        st.plotly_chart(fig, use_container_width=True)
        st.info("**Insight:** U-Shaped weights first and last touch 40% each. Channels that differ significantly between models are mid-funnel nurturing channels.")

    else:
        fig = px.bar(model_df, x="channel_name", y="time_decay",
                     title="Time Decay Attribution — More Credit to Recent Touches",
                     color="channel_name")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Model Comparison Table")
    display = model_df.copy()
    for col in ["first_touch","last_touch","linear","time_decay","u_shaped"]:
        display[col] = display[col].apply(lambda x: f"${x:,.0f}")
    st.dataframe(display.rename(columns={
        "channel_name":"Channel","source_platform":"Source",
        "first_touch":"First Touch","last_touch":"Last Touch",
        "linear":"Linear","time_decay":"Time Decay","u_shaped":"U-Shaped",
        "conversions":"Conversions"}), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — SPEND & ROI
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[1]:
    st.title("Spend & ROI by Channel")
    st.caption("Source: Google Ads · Meta Ads — daily spend vs. attributed revenue")

    spend_df = q("""
        SELECT ch.channel_name, ch.source_platform,
               ROUND(SUM(fs.daily_spend),2) as total_spend,
               SUM(fs.impressions) as impressions,
               SUM(fs.clicks) as clicks,
               ROUND(AVG(fs.ctr)*100,2) as avg_ctr_pct,
               ROUND(AVG(fs.cpc),2) as avg_cpc,
               ROUND(AVG(fs.cpm),2) as avg_cpm
        FROM fact_spend fs
        JOIN dim_channel ch ON fs.channel_id = ch.channel_id
        WHERE fs.spend_date BETWEEN ? AND ?
        GROUP BY ch.channel_name, ch.source_platform
        ORDER BY total_spend DESC
    """, (start_d, end_d))

    rev_df = q("""
        SELECT ch.channel_name,
               ROUND(SUM(fa.credit_linear * fa.conversion_revenue),2) as attributed_rev
        FROM fact_attribution fa
        JOIN dim_channel ch ON fa.channel_id = ch.channel_id
        JOIN fact_conversions fc ON fa.conversion_id = fc.conversion_id
        WHERE fc.conversion_date BETWEEN ? AND ?
        GROUP BY ch.channel_name
    """, (start_d, end_d))

    roi_df = spend_df.merge(rev_df, on="channel_name", how="left").fillna(0)
    roi_df["roas"] = (roi_df["attributed_rev"] / roi_df["total_spend"]).round(2)
    roi_df["roas"] = roi_df["roas"].replace([float("inf"),float("nan")], 0)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Paid Spend", f"${roi_df['total_spend'].sum():,.0f}")
    c2.metric("Total Attributed Rev", f"${roi_df['attributed_rev'].sum():,.0f}")
    best = roi_df.loc[roi_df["roas"].idxmax()]
    c3.metric("Best ROAS Channel", best["channel_name"], f"{best['roas']:.1f}x")
    c4.metric("Total Impressions", f"{roi_df['impressions'].sum():,}")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(roi_df, x="channel_name", y=["total_spend","attributed_rev"],
                     barmode="group", title="Spend vs Attributed Revenue",
                     labels={"value":"Amount ($)","channel_name":"Channel"})
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(roi_df[roi_df["roas"]>0], x="channel_name", y="roas",
                     title="ROAS by Channel (Linear Attribution)",
                     color="roas", color_continuous_scale="RdYlGn")
        fig.add_hline(y=1, line_dash="dash", line_color="red", annotation_text="Break Even")
        st.plotly_chart(fig, use_container_width=True)

    daily_spend = q("""
        SELECT fs.spend_date, ch.channel_name, SUM(fs.daily_spend) as spend
        FROM fact_spend fs JOIN dim_channel ch ON fs.channel_id=ch.channel_id
        WHERE fs.spend_date BETWEEN ? AND ?
        GROUP BY fs.spend_date, ch.channel_name
        ORDER BY fs.spend_date
    """, (start_d, end_d))
    if not daily_spend.empty:
        fig = px.line(daily_spend, x="spend_date", y="spend", color="channel_name",
                      title="Daily Spend Trend by Channel")
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — FULL FUNNEL
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[2]:
    st.title("Full Funnel Analysis")
    st.caption("Awareness → Consideration → Conversion · Source: GA4 · HubSpot · Segment")

    funnel_df = q("""
        SELECT
            COUNT(DISTINCT ft.customer_id) as prospects,
            COUNT(DISTINCT CASE WHEN ft.touch_type IN ('Click','Email Click','SMS Click') THEN ft.customer_id END) as engaged,
            COUNT(DISTINCT fc.customer_id) as converted,
            COUNT(DISTINCT CASE WHEN fc.conversion_type='Trial Start' THEN fc.customer_id END) as trials,
            COUNT(DISTINCT CASE WHEN fc.conversion_type='Subscription Start' THEN fc.customer_id END) as subscribers
        FROM fact_touchpoints ft
        LEFT JOIN fact_conversions fc ON ft.customer_id=fc.customer_id
        WHERE ft.touch_date BETWEEN ? AND ?
    """, (start_d, end_d))

    r = funnel_df.iloc[0]
    fig = go.Figure(go.Funnel(
        y=["Prospects Reached","Engaged (Clicked)","Converted","Trial Start","Paid Subscriber"],
        x=[r["prospects"],r["engaged"],r["converted"],r["trials"],r["subscribers"]],
        textinfo="value+percent initial",
        marker_color=["#1F4E79","#2E75B6","#4BACC6","#70AD47","#A9D18E"]
    ))
    fig.update_layout(title="Customer Acquisition Funnel")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Conversion Rate by Channel")
    ch_funnel = q("""
        SELECT ch.channel_name, ch.source_platform,
               COUNT(DISTINCT ft.customer_id) as reached,
               COUNT(DISTINCT fc.customer_id) as converted,
               ROUND(COUNT(DISTINCT fc.customer_id)*100.0/
                     NULLIF(COUNT(DISTINCT ft.customer_id),0),1) as cvr_pct
        FROM fact_touchpoints ft
        JOIN dim_channel ch ON ft.channel_id=ch.channel_id
        LEFT JOIN fact_conversions fc ON ft.customer_id=fc.customer_id
            AND fc.conversion_date BETWEEN ? AND ?
        WHERE ft.touch_date BETWEEN ? AND ?
        GROUP BY ch.channel_name, ch.source_platform
        ORDER BY cvr_pct DESC
    """, (start_d, end_d, start_d, end_d))
    fig = px.bar(ch_funnel, x="channel_name", y="cvr_pct",
                 color="source_platform", title="Conversion Rate % by Channel",
                 labels={"cvr_pct":"CVR %","channel_name":"Channel"})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Touches to Convert")
    touch_dist = q("""
        SELECT touches_to_convert, COUNT(*) as conversions
        FROM fact_conversions
        WHERE conversion_date BETWEEN ? AND ?
        GROUP BY touches_to_convert ORDER BY touches_to_convert
    """, (start_d, end_d))
    fig = px.bar(touch_dist, x="touches_to_convert", y="conversions",
                 title="Distribution: Number of Touches Before Conversion",
                 labels={"touches_to_convert":"Touches","conversions":"Conversions"})
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — LTV & RETENTION
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[3]:
    st.title("LTV & Retention Analytics")
    st.caption("Source: HubSpot · Stripe · Mixpanel — 30/60/90/180/365-day cohort windows")

    ltv_df = q("""
        SELECT dc.acquisition_channel,
               COUNT(DISTINCT fo.customer_id) as customers,
               ROUND(SUM(CASE WHEN julianday(fo.order_date)-julianday(dc.first_seen_date)<=30
                   THEN fo.revenue ELSE 0 END)/NULLIF(COUNT(DISTINCT fo.customer_id),0),2) as ltv_30,
               ROUND(SUM(CASE WHEN julianday(fo.order_date)-julianday(dc.first_seen_date)<=60
                   THEN fo.revenue ELSE 0 END)/NULLIF(COUNT(DISTINCT fo.customer_id),0),2) as ltv_60,
               ROUND(SUM(CASE WHEN julianday(fo.order_date)-julianday(dc.first_seen_date)<=90
                   THEN fo.revenue ELSE 0 END)/NULLIF(COUNT(DISTINCT fo.customer_id),0),2) as ltv_90,
               ROUND(SUM(CASE WHEN julianday(fo.order_date)-julianday(dc.first_seen_date)<=180
                   THEN fo.revenue ELSE 0 END)/NULLIF(COUNT(DISTINCT fo.customer_id),0),2) as ltv_180,
               ROUND(SUM(CASE WHEN julianday(fo.order_date)-julianday(dc.first_seen_date)<=365
                   THEN fo.revenue ELSE 0 END)/NULLIF(COUNT(DISTINCT fo.customer_id),0),2) as ltv_365
        FROM fact_orders fo
        JOIN dim_customer dc ON fo.customer_id=dc.customer_id
        GROUP BY dc.acquisition_channel
        ORDER BY ltv_365 DESC
    """)

    c1,c2,c3 = st.columns(3)
    if not ltv_df.empty:
        best = ltv_df.iloc[0]
        c1.metric("Best Channel 365-Day LTV", best["acquisition_channel"], f"${best['ltv_365']:,.2f}")
        c2.metric("Avg 365-Day LTV (All)", f"${ltv_df['ltv_365'].mean():,.2f}")
        c3.metric("LTV Spread (Best vs Worst)", f"${ltv_df['ltv_365'].max()-ltv_df['ltv_365'].min():,.2f}")

    st.divider()
    ltv_melt = ltv_df.melt(id_vars=["acquisition_channel"],
        value_vars=["ltv_30","ltv_60","ltv_90","ltv_180","ltv_365"],
        var_name="Window", value_name="LTV")
    ltv_melt["Window"] = ltv_melt["Window"].str.replace("ltv_","").apply(lambda x: f"{x}-Day")
    fig = px.line(ltv_melt, x="Window", y="LTV", color="acquisition_channel",
                  markers=True, title="LTV Curve by Acquisition Channel",
                  labels={"LTV":"Avg Revenue per Customer ($)"})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Churn & Retention by Segment")
    churn_df = q("""
        SELECT dc.segment,
               COUNT(*) as total,
               SUM(CASE WHEN fs.status='Cancelled' THEN 1 ELSE 0 END) as churned,
               SUM(CASE WHEN fs.status='Active' THEN 1 ELSE 0 END) as active,
               ROUND(SUM(CASE WHEN fs.status='Cancelled' THEN 1 ELSE 0 END)*100.0/COUNT(*),1) as churn_rate
        FROM fact_subscriptions fs
        JOIN dim_customer dc ON fs.customer_id=dc.customer_id
        GROUP BY dc.segment ORDER BY churn_rate DESC
    """)
    col1,col2 = st.columns(2)
    with col1:
        fig = px.bar(churn_df, x="segment", y="churn_rate",
                     title="Churn Rate by Segment (%)",
                     color="churn_rate", color_continuous_scale="RdYlGn_r")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.pie(churn_df, names="segment", values="active",
                     title="Active Subscribers by Segment")
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — CART & REACTIVATION
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[4]:
    st.title("Cart Recovery & Reactivation Analytics")
    st.caption("Source: Klaviyo · Mixpanel — abandoned cart, win-back, and at-risk campaigns")

    cart_df = q("""
        SELECT event_type, COUNT(*) as events,
               ROUND(AVG(cart_value),2) as avg_value,
               ROUND(SUM(cart_value),2) as total_value
        FROM fact_cart_events
        WHERE event_date BETWEEN ? AND ?
        GROUP BY event_type
    """, (start_d, end_d))

    abandons = cart_df[cart_df["event_type"]=="Abandon"]["events"].sum() if len(cart_df) else 0
    recovers = cart_df[cart_df["event_type"]=="Recover"]["events"].sum() if len(cart_df) else 0
    rec_rate = round(recovers/abandons*100,1) if abandons else 0

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Cart Abandons", f"{abandons:,}")
    c2.metric("Carts Recovered", f"{recovers:,}")
    c3.metric("Recovery Rate", f"{rec_rate}%")
    avg_val = cart_df[cart_df["event_type"]=="Abandon"]["avg_value"].mean() if len(cart_df) else 0
    c4.metric("Avg Abandoned Value", f"${avg_val:,.2f}")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        offer_df = q("""
            SELECT offer_applied, COUNT(*) as recoveries,
                   ROUND(AVG(cart_value),2) as avg_value
            FROM fact_cart_events
            WHERE event_type='Recover' AND offer_applied IS NOT NULL
            AND event_date BETWEEN ? AND ?
            GROUP BY offer_applied ORDER BY recoveries DESC
        """, (start_d, end_d))
        fig = px.bar(offer_df, x="offer_applied", y="recoveries",
                     title="Cart Recovery by Offer Type",
                     labels={"offer_applied":"Offer","recoveries":"Recoveries"})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        ch_rec = q("""
            SELECT recovery_channel, COUNT(*) as recoveries
            FROM fact_cart_events
            WHERE event_type='Recover' AND recovery_channel IS NOT NULL
            AND event_date BETWEEN ? AND ?
            GROUP BY recovery_channel ORDER BY recoveries DESC
        """, (start_d, end_d))
        fig = px.pie(ch_rec, names="recovery_channel", values="recoveries",
                     title="Recovery Channel Mix")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Reactivation Campaign Performance")
    react_df = q("""
        SELECT trigger_reason, offer_type,
               COUNT(*) as campaigns_sent,
               SUM(CASE WHEN converted THEN 1 ELSE 0 END) as conversions,
               ROUND(SUM(CASE WHEN converted THEN 1 ELSE 0 END)*100.0/COUNT(*),1) as cvr,
               ROUND(SUM(COALESCE(conversion_revenue,0)),2) as revenue_won_back
        FROM fact_reactivation_campaigns
        WHERE trigger_date BETWEEN ? AND ?
        GROUP BY trigger_reason, offer_type
        ORDER BY cvr DESC
    """, (start_d, end_d))

    c1,c2,c3 = st.columns(3)
    c1.metric("Reactivation Campaigns", f"{react_df['campaigns_sent'].sum():,}")
    c2.metric("Customers Won Back", f"{react_df['conversions'].sum():,}")
    c3.metric("Revenue Won Back", f"${react_df['revenue_won_back'].sum():,.0f}")

    fig = px.scatter(react_df, x="offer_type", y="cvr", size="campaigns_sent",
                     color="trigger_reason", title="Reactivation CVR by Offer Type & Trigger",
                     labels={"cvr":"Conversion Rate %","offer_type":"Offer Type"})
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — BRAND & SHARE OF VOICE
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[5]:
    st.title("Brand Health & Share of Voice")
    st.caption("Non-paid analytics: organic reach, sentiment, NPS, branded search · Source: GA4 · HubSpot")

    brand_df = q("""
        SELECT bs.signal_date, ch.channel_name,
               bs.share_of_voice, bs.organic_reach, bs.sentiment_score,
               bs.mentions, bs.branded_searches, bs.nps_score, bs.nps_responses
        FROM fact_brand_signals bs
        JOIN dim_channel ch ON bs.channel_id=ch.channel_id
        WHERE bs.signal_date BETWEEN ? AND ?
        ORDER BY bs.signal_date
    """, (start_d, end_d))

    if not brand_df.empty:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Avg Share of Voice", f"{brand_df['share_of_voice'].mean()*100:.1f}%")
        c2.metric("Avg NPS Score", f"{brand_df['nps_score'].mean():.1f}")
        c3.metric("Avg Sentiment", f"{brand_df['sentiment_score'].mean():.2f}")
        c4.metric("Total Branded Searches", f"{brand_df['branded_searches'].sum():,}")

        st.divider()
        col1,col2 = st.columns(2)
        with col1:
            fig = px.line(brand_df, x="signal_date", y="share_of_voice",
                          color="channel_name", title="Share of Voice Over Time",
                          labels={"share_of_voice":"Share of Voice","signal_date":"Date"})
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.line(brand_df, x="signal_date", y="nps_score",
                          color="channel_name", title="NPS Score Trend",
                          labels={"nps_score":"NPS","signal_date":"Date"})
            fig.add_hline(y=50, line_dash="dash", annotation_text="Good NPS Threshold")
            st.plotly_chart(fig, use_container_width=True)

        fig = px.scatter(brand_df, x="sentiment_score", y="share_of_voice",
                         size="organic_reach", color="channel_name",
                         title="Sentiment vs Share of Voice (bubble = organic reach)",
                         labels={"sentiment_score":"Sentiment (-1 to 1)",
                                 "share_of_voice":"Share of Voice"})
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7 — DATA SOURCES
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[6]:
    st.title("Data Sources & Schema")
    st.caption("Simulated platform data — no real API connections")

    platforms = {
        "GA4 (Google Analytics 4)": {
            "color": "#E37400",
            "tables": ["fact_touchpoints (Organic, Direct)", "fact_brand_signals"],
            "what": "Web sessions, traffic sources, organic visits, landing page events, goal completions"
        },
        "Google Ads": {
            "color": "#4285F4",
            "tables": ["fact_spend (Paid Search)", "fact_touchpoints (Paid Search)"],
            "what": "Keyword-level spend, impressions, clicks, CTR, CPC, CPM, quality scores"
        },
        "Meta Ads Manager": {
            "color": "#1877F2",
            "tables": ["fact_spend (Paid Social)", "fact_touchpoints (Paid Social)"],
            "what": "Campaign and ad set spend, ROAS, reach, frequency, CPM by audience segment"
        },
        "HubSpot (CRM)": {
            "color": "#FF7A59",
            "tables": ["dim_customer", "fact_conversions", "fact_brand_signals (NPS)"],
            "what": "Contact lifecycle stages, deal pipeline, email sequences, NPS surveys, form submissions"
        },
        "Klaviyo": {
            "color": "#22BC66",
            "tables": ["fact_touchpoints (Email, SMS)", "fact_cart_events", "fact_reactivation_campaigns"],
            "what": "Email/SMS sends, opens, clicks, abandoned cart flows, win-back sequences, offer redemptions"
        },
        "Segment (CDP)": {
            "color": "#52BD94",
            "tables": ["fact_attribution", "fact_touchpoints (identity stitching)"],
            "what": "Cross-platform identity resolution, event routing, customer journey stitching across all sources"
        },
        "Mixpanel": {
            "color": "#7856FF",
            "tables": ["fact_touchpoints (In-App)", "fact_subscriptions"],
            "what": "In-app events, feature usage, activity levels, session frequency — feeds at-risk detection"
        },
    }

    for platform, info in platforms.items():
        with st.expander(f"**{platform}**", expanded=False):
            col1,col2 = st.columns([1,2])
            with col1:
                st.markdown(f"**Tables fed:**")
                for t in info["tables"]:
                    st.markdown(f"- `{t}`")
            with col2:
                st.markdown(f"**What it simulates:**")
                st.markdown(info["what"])

    st.divider()
    st.subheader("Database Summary")
    counts = q("""
        SELECT 'dim_customer' as tbl, COUNT(*) as rows FROM dim_customer UNION ALL
        SELECT 'dim_channel', COUNT(*) FROM dim_channel UNION ALL
        SELECT 'dim_campaign', COUNT(*) FROM dim_campaign UNION ALL
        SELECT 'dim_product', COUNT(*) FROM dim_product UNION ALL
        SELECT 'fact_touchpoints', COUNT(*) FROM fact_touchpoints UNION ALL
        SELECT 'fact_conversions', COUNT(*) FROM fact_conversions UNION ALL
        SELECT 'fact_spend', COUNT(*) FROM fact_spend UNION ALL
        SELECT 'fact_subscriptions', COUNT(*) FROM fact_subscriptions UNION ALL
        SELECT 'fact_orders', COUNT(*) FROM fact_orders UNION ALL
        SELECT 'fact_cart_events', COUNT(*) FROM fact_cart_events UNION ALL
        SELECT 'fact_reactivation_campaigns', COUNT(*) FROM fact_reactivation_campaigns UNION ALL
        SELECT 'fact_brand_signals', COUNT(*) FROM fact_brand_signals UNION ALL
        SELECT 'fact_attribution', COUNT(*) FROM fact_attribution
    """)
    counts["rows"] = counts["rows"].apply(lambda x: f"{x:,}")
    st.dataframe(counts.rename(columns={"tbl":"Table","rows":"Row Count"}),
                 use_container_width=True, hide_index=True)
    st.caption(f"**Total: 105,895 synthetic rows across 14 tables · 2023–2024**")
