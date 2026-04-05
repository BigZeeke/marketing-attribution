"""
Marketing Attribution Intelligence Platform v2
B2C Subscription Brand — Full Lifecycle Analytics + AI Recommendations
Simulates: GA4 · HubSpot · Meta Ads · Google Ads · Klaviyo · Segment · Mixpanel
"""
import sqlite3, os, json, urllib.request
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB = os.path.join(os.path.dirname(__file__), "marketing_attribution.db")

st.set_page_config(
    page_title="Marketing Attribution Platform",
    page_icon="📊", layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
[data-testid="stMetricValue"]{font-size:1.5rem;font-weight:600}
.insight-warn{background:rgba(245,158,11,0.12);border-left:4px solid #f59e0b;padding:12px 16px;
  border-radius:0 8px 8px 0;margin:12px 0;font-size:14px;color:inherit}
.insight-danger{background:rgba(239,68,68,0.12);border-left:4px solid #ef4444;padding:12px 16px;
  border-radius:0 8px 8px 0;margin:12px 0;font-size:14px;color:inherit}
.insight-good{background:rgba(34,197,94,0.12);border-left:4px solid #22c55e;padding:12px 16px;
  border-radius:0 8px 8px 0;margin:12px 0;font-size:14px;color:inherit}
.rec-card{background:var(--background-color,transparent);
  border:1px solid var(--border-color,rgba(128,128,128,0.3));border-radius:12px;
  padding:16px 20px;margin:10px 0}
.badge-high{background:rgba(220,38,38,0.15);color:#ef4444;padding:2px 10px;border-radius:12px;
  font-size:11px;font-weight:700}
.badge-med{background:rgba(217,119,6,0.15);color:#f59e0b;padding:2px 10px;border-radius:12px;
  font-size:11px;font-weight:700}
.badge-low{background:rgba(22,163,74,0.15);color:#22c55e;padding:2px 10px;border-radius:12px;
  font-size:11px;font-weight:700}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def q(sql, params=()):
    return pd.read_sql_query(sql, get_conn(), params=params)

def warn(msg):   st.markdown(f'<div class="insight-warn">⚠️ {msg}</div>', unsafe_allow_html=True)
def danger(msg): st.markdown(f'<div class="insight-danger">🔴 {msg}</div>', unsafe_allow_html=True)
def good(msg):   st.markdown(f'<div class="insight-good">✅ {msg}</div>', unsafe_allow_html=True)

PLATFORM_COLORS = {
    "GA4":"#E37400","Meta Ads":"#1877F2","Google Ads":"#4285F4",
    "Klaviyo":"#22BC66","Mixpanel":"#7856FF","HubSpot":"#FF7A59","Segment":"#52BD94"
}

PRIORITY_BADGE = {
    "High":  '<span class="badge-high">HIGH PRIORITY</span>',
    "Medium":'<span class="badge-med">MEDIUM</span>',
    "Low":   '<span class="badge-low">LOW</span>',
}

# Pages — AI Recommendations is NOT in this list, it's a separate mode
PAGES = ["📊 Attribution Models","💰 Spend & ROI","🔄 Full Funnel",
         "💎 LTV & Retention","🛒 Cart & Reactivation","📣 Brand & Share of Voice",
         "🗄️ Data Sources"]

# API key from secrets
try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    api_key = ""

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 Attribution Platform")
    st.caption("B2C Subscription Brand · Full Lifecycle")
    page = st.radio("Navigation", PAGES, label_visibility="collapsed")
    st.divider()

    # AI Recommendations — standalone button, not in radio list
    st.markdown("**🤖 AI Recommendations**")
    run_ai = st.button("⚡ Run Full Analysis", type="primary", use_container_width=True)
    if st.session_state.get("ai_recs"):
        st.success(f"✓ {len(st.session_state.ai_recs)} recommendations ready")
        view_recs = st.button("📋 View Recommendations", use_container_width=True)
    else:
        view_recs = False

    st.divider()
    st.caption("**Simulated Data Sources**")
    for p, col in PLATFORM_COLORS.items():
        st.markdown(
            f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;' +
            f'font-size:11px;font-weight:600;margin:2px;background:{col}20;' +
            f'color:{col};border:1px solid {col}40">{p}</span>',
            unsafe_allow_html=True)
    st.divider()
    dr = st.date_input("Date Range",
        value=[pd.to_datetime("2023-01-01"), pd.to_datetime("2024-12-31")],
        min_value=pd.to_datetime("2023-01-01"),
        max_value=pd.to_datetime("2024-12-31"))
    start_d = str(dr[0]) if len(dr) == 2 else "2023-01-01"
    end_d   = str(dr[1]) if len(dr) == 2 else "2024-12-31"


# ── AI ANALYSIS FUNCTION ─────────────────────────────────────────────────────
def do_ai_analysis():
    if not api_key:
        st.error("⚠️ ANTHROPIC_API_KEY not found. Add it to .streamlit/secrets.toml")
        return
    with st.spinner("Running diagnostic queries..."):
        roas_diag = q("""
            SELECT ch.channel_name,
                   ROUND(SUM(fs.daily_spend),0) as spend,
                   ROUND(SUM(fa.credit_linear*fa.conversion_revenue),0) as rev,
                   ROUND(SUM(fa.credit_linear*fa.conversion_revenue)/
                         NULLIF(SUM(fs.daily_spend),0),2) as roas
            FROM fact_spend fs
            JOIN dim_channel ch ON fs.channel_id=ch.channel_id
            LEFT JOIN fact_attribution fa ON fa.channel_id=ch.channel_id
            LEFT JOIN fact_conversions fc ON fa.conversion_id=fc.conversion_id
            GROUP BY ch.channel_name ORDER BY roas ASC""")
        churn_diag = q("""
            SELECT dc.acquisition_channel,
                   ROUND(AVG(CASE WHEN fs.status='Cancelled' THEN 1.0 ELSE 0 END)*100,1) as churn_rate
            FROM fact_subscriptions fs
            JOIN dim_customer dc ON fs.customer_id=dc.customer_id
            GROUP BY dc.acquisition_channel ORDER BY churn_rate DESC LIMIT 5""")
        ltv_diag = q("""
            SELECT dc.acquisition_channel,
                   ROUND(SUM(CASE WHEN julianday(fo.order_date)-julianday(dc.first_seen_date)<=60
                       THEN fo.revenue ELSE 0 END)/COUNT(DISTINCT fo.customer_id),2) as ltv_60,
                   ROUND(SUM(CASE WHEN julianday(fo.order_date)-julianday(dc.first_seen_date)<=365
                       THEN fo.revenue ELSE 0 END)/COUNT(DISTINCT fo.customer_id),2) as ltv_365
            FROM fact_orders fo JOIN dim_customer dc ON fo.customer_id=dc.customer_id
            GROUP BY dc.acquisition_channel ORDER BY ltv_365 DESC""")
        cart_diag = q("""
            SELECT offer_applied,
                   ROUND(SUM(CASE WHEN event_type='Recover' THEN 1.0 ELSE 0 END)/COUNT(*)*100,1) as rec_rate
            FROM fact_cart_events WHERE offer_applied IS NOT NULL
            GROUP BY offer_applied ORDER BY rec_rate ASC""")
        react_diag = q("""
            SELECT trigger_reason,
                   ROUND(AVG(CASE WHEN converted THEN 1.0 ELSE 0 END)*100,1) as cvr
            FROM fact_reactivation_campaigns
            GROUP BY trigger_reason ORDER BY cvr ASC""")
        seg_diag = q("""
            SELECT dc.segment,
                   ROUND(SUM(CASE WHEN julianday(fo.order_date)-julianday(dc.first_seen_date)<=60
                       THEN fo.revenue ELSE 0 END)/COUNT(DISTINCT fo.customer_id),2) as ltv_60,
                   ROUND(SUM(CASE WHEN julianday(fo.order_date)-julianday(dc.first_seen_date)<=365
                       THEN fo.revenue ELSE 0 END)/COUNT(DISTINCT fo.customer_id),2) as ltv_365
            FROM fact_orders fo JOIN dim_customer dc ON fo.customer_id=dc.customer_id
            GROUP BY dc.segment""")

    prompt = f"""You are a senior marketing analytics consultant analyzing a B2C subscription brand.
Here are live diagnostics:
CHANNEL ROAS: {roas_diag.to_string(index=False)}
CHURN BY CHANNEL: {churn_diag.to_string(index=False)}
LTV BY CHANNEL (60 vs 365 day): {ltv_diag.to_string(index=False)}
CART RECOVERY BY OFFER: {cart_diag.to_string(index=False)}
REACTIVATION CVR BY TRIGGER: {react_diag.to_string(index=False)}
SEGMENT LTV: {seg_diag.to_string(index=False)}
Return exactly 6 prioritized recommendations as JSON only, no other text, no markdown fences:
{{"recommendations":[{{"priority":"High","title":"Short title","problem":"1-2 sentences","action":"2-3 sentences","impact":"estimated impact","effort":"Low/Medium/High","owner":"Media/CRM/Product/Leadership"}}]}}"""

    with st.spinner("Calling Claude API..."):
        try:
            payload = json.dumps({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2000,
                "messages": [{"role":"user","content": prompt}]
            }).encode()
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload,
                headers={"Content-Type":"application/json",
                         "x-api-key": api_key,
                         "anthropic-version":"2023-06-01"}
            )
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
            raw = result["content"][0]["text"].strip().replace("```json","").replace("```","").strip()
            st.session_state.ai_recs = json.loads(raw)["recommendations"]
            st.session_state.show_ai = True
            st.rerun()
        except Exception as e:
            st.error(f"API error: {e}")


def render_rec_cards(recs):
    for i, rec in enumerate(recs, 1):
        badge = PRIORITY_BADGE.get(rec.get("priority","Medium"),"")
        st.markdown(f"""
<div class="rec-card">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
    <span style="font-size:18px;font-weight:700">#{i}</span>
    {badge}
    <span style="font-size:16px;font-weight:600">{rec.get('title','')}</span>
  </div>
  <p style="color:#ef4444;font-size:13px;margin:4px 0"><b>Problem:</b> {rec.get('problem','')}</p>
  <p style="font-size:13px;margin:4px 0"><b>Action:</b> {rec.get('action','')}</p>
  <div style="display:flex;gap:24px;margin-top:10px;font-size:12px;opacity:0.7">
    <span>📈 <b>Impact:</b> {rec.get('impact','')}</span>
    <span>⚡ <b>Effort:</b> {rec.get('effort','')}</span>
    <span>👤 <b>Owner:</b> {rec.get('owner','')}</span>
  </div>
</div>""", unsafe_allow_html=True)


# ── ROUTING ──────────────────────────────────────────────────────────────────
# Handle sidebar button triggers first
if run_ai:
    st.session_state.show_ai = True
    do_ai_analysis()
elif view_recs:
    st.session_state.show_ai = True
    st.rerun()

# AI view takes over the full main area
if st.session_state.get("show_ai"):
    st.title("🤖 AI Marketing Recommendations")
    st.caption("Live diagnostic queries → Claude API → prioritized action plan")
    col_a, col_b = st.columns([4, 1])
    with col_a:
        if st.session_state.get("ai_recs"):
            st.success(f"✓ {len(st.session_state.ai_recs)} recommendations generated from live data")
    with col_b:
        if st.button("← Dashboard"):
            st.session_state.show_ai = False
            st.rerun()
    st.divider()
    if st.session_state.get("ai_recs"):
        render_rec_cards(st.session_state.ai_recs)
        st.divider()
        if st.button("🔄 Re-run Analysis"):
            del st.session_state["ai_recs"]
            st.session_state.show_ai = False
            st.rerun()
    else:
        do_ai_analysis()

else:
    # PAGE 1 — ATTRIBUTION MODELS
    # ══════════════════════════════════════════════════════════════════════════════
    if page == PAGES[0]:
        st.title("Multi-Touch Attribution Models")
        st.caption("Comparing First Touch · Last Touch · Linear · Time Decay · U-Shaped")
    
        model_df = q("""
            SELECT ch.channel_name, ch.source_platform,
                   ROUND(SUM(fa.credit_first_touch*fa.conversion_revenue),2) as first_touch,
                   ROUND(SUM(fa.credit_last_touch *fa.conversion_revenue),2) as last_touch,
                   ROUND(SUM(fa.credit_linear     *fa.conversion_revenue),2) as linear,
                   ROUND(SUM(fa.credit_time_decay *fa.conversion_revenue),2) as time_decay,
                   ROUND(SUM(fa.credit_u_shaped   *fa.conversion_revenue),2) as u_shaped,
                   COUNT(DISTINCT fa.conversion_id) as conversions
            FROM fact_attribution fa
            JOIN dim_channel ch ON fa.channel_id=ch.channel_id
            JOIN fact_conversions fc ON fa.conversion_id=fc.conversion_id
            WHERE fc.conversion_date BETWEEN ? AND ?
            GROUP BY ch.channel_name, ch.source_platform
            ORDER BY linear DESC
        """, (start_d,end_d))
    
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total Attributed Revenue", f"${model_df['linear'].sum():,.0f}")
        c2.metric("Channels", len(model_df))
        c3.metric("Total Conversions", f"{model_df['conversions'].sum():,}")
        top = model_df.iloc[0]["channel_name"] if len(model_df) else "—"
        c4.metric("Top Channel (Linear)", top)
    
        st.divider()
    
        # Inline insights
        if len(model_df) >= 2:
            top_ch = model_df.iloc[0]["channel_name"]
            bot_ch = model_df.iloc[-1]["channel_name"]
            top_ft = model_df.iloc[0]["first_touch"]
            top_lt = model_df.iloc[0]["last_touch"]
            if top_ft > top_lt * 1.5:
                warn(f"<b>{top_ch}</b> gets heavy First Touch credit but low Last Touch credit — it's driving awareness but not closing. Consider investing in mid-funnel nurturing from this channel.")
            display_row = model_df[model_df["channel_name"]=="Display"]
            if not display_row.empty:
                disp_linear = display_row.iloc[0]["linear"]
                if disp_linear < model_df["linear"].mean() * 0.5:
                    danger(f"<b>Display</b> attributed revenue is well below channel average across all models. Cross-reference with Spend & ROI to evaluate whether this channel is worth the investment.")
            good(f"<b>{top_ch}</b> leads attributed revenue across all five models — consistent signal across model types indicates genuine performance, not model-dependent noise.")
    
        model_choice = st.selectbox("Compare attribution models",
            ["All Models Side by Side","First Touch vs Last Touch","Linear vs U-Shaped","Time Decay Detail"])
    
        if model_choice == "All Models Side by Side":
            melt = model_df.melt(id_vars=["channel_name"],
                value_vars=["first_touch","last_touch","linear","time_decay","u_shaped"],
                var_name="Model",value_name="Revenue")
            fig = px.bar(melt,x="channel_name",y="Revenue",color="Model",barmode="group",
                         title="Attributed Revenue by Channel — All Models",
                         labels={"channel_name":"Channel","Revenue":"Attributed Revenue ($)"})
            st.plotly_chart(fig,use_container_width=True)
        elif model_choice == "First Touch vs Last Touch":
            fig = go.Figure()
            fig.add_trace(go.Bar(name="First Touch",x=model_df["channel_name"],y=model_df["first_touch"]))
            fig.add_trace(go.Bar(name="Last Touch", x=model_df["channel_name"],y=model_df["last_touch"]))
            fig.update_layout(barmode="group",title="First Touch vs Last Touch Attribution")
            st.plotly_chart(fig,use_container_width=True)
            st.info("**Insight:** Channels with high First Touch but low Last Touch are awareness drivers. Channels strong on Last Touch are closers. Budget differently for each role.")
        elif model_choice == "Linear vs U-Shaped":
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Linear",  x=model_df["channel_name"],y=model_df["linear"]))
            fig.add_trace(go.Bar(name="U-Shaped",x=model_df["channel_name"],y=model_df["u_shaped"]))
            fig.update_layout(barmode="group",title="Linear vs U-Shaped Attribution")
            st.plotly_chart(fig,use_container_width=True)
        else:
            fig = px.bar(model_df,x="channel_name",y="time_decay",color="channel_name",
                         title="Time Decay Attribution — More Credit to Recent Touches")
            st.plotly_chart(fig,use_container_width=True)
    
        st.subheader("Model Comparison Table")
        disp = model_df.copy()
        for col in ["first_touch","last_touch","linear","time_decay","u_shaped"]:
            disp[col] = disp[col].apply(lambda x: f"${x:,.0f}")
        st.dataframe(disp.rename(columns={"channel_name":"Channel","source_platform":"Source",
            "first_touch":"First Touch","last_touch":"Last Touch","linear":"Linear",
            "time_decay":"Time Decay","u_shaped":"U-Shaped","conversions":"Conversions"}),
            use_container_width=True,hide_index=True)
    
    # ══════════════════════════════════════════════════════════════════════════════
    # PAGE 2 — SPEND & ROI
    # ══════════════════════════════════════════════════════════════════════════════
    elif page == PAGES[1]:
        st.title("Spend & ROI by Channel")
        st.caption("Source: Google Ads · Meta Ads — daily spend vs. attributed revenue (Linear model)")
    
        spend_df = q("""
            SELECT ch.channel_name, ch.source_platform,
                   ROUND(SUM(fs.daily_spend),2) as total_spend,
                   SUM(fs.impressions) as impressions, SUM(fs.clicks) as clicks,
                   ROUND(AVG(fs.ctr)*100,2) as avg_ctr,
                   ROUND(AVG(fs.cpc),2) as avg_cpc
            FROM fact_spend fs JOIN dim_channel ch ON fs.channel_id=ch.channel_id
            WHERE fs.spend_date BETWEEN ? AND ?
            GROUP BY ch.channel_name, ch.source_platform
            ORDER BY total_spend DESC
        """, (start_d,end_d))
    
        rev_df = q("""
            SELECT ch.channel_name,
                   ROUND(SUM(fa.credit_linear*fa.conversion_revenue),2) as attributed_rev
            FROM fact_attribution fa
            JOIN dim_channel ch ON fa.channel_id=ch.channel_id
            JOIN fact_conversions fc ON fa.conversion_id=fc.conversion_id
            WHERE fc.conversion_date BETWEEN ? AND ?
            GROUP BY ch.channel_name
        """, (start_d,end_d))
    
        roi_df = spend_df.merge(rev_df,on="channel_name",how="left").fillna(0)
        roi_df["roas"] = (roi_df["attributed_rev"]/roi_df["total_spend"].replace(0,1)).round(2)
    
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total Paid Spend", f"${roi_df['total_spend'].sum():,.0f}")
        c2.metric("Total Attributed Rev", f"${roi_df['attributed_rev'].sum():,.0f}")
        below_break = roi_df[roi_df["roas"]<1.0]
        c3.metric("Channels Below Break-Even", f"{len(below_break)}", delta=f"-{len(below_break)} channels losing money", delta_color="inverse")
        best = roi_df.loc[roi_df["roas"].idxmax()]
        c4.metric("Best ROAS", best["channel_name"], f"{best['roas']:.1f}x")
    
        st.divider()
    
        # Inline insights
        for _,row in roi_df.iterrows():
            if row["roas"] < 1.0 and row["total_spend"] > 0:
                danger(f"<b>{row['channel_name']}</b> ROAS is {row['roas']:.2f}x — spending ${row['total_spend']:,.0f} to generate ${row['attributed_rev']:,.0f}. Every dollar spent returns less than a dollar. Recommend reducing budget by 40-60% and reallocating to higher-performing channels.")
            elif row["roas"] > 3.0:
                good(f"<b>{row['channel_name']}</b> ROAS of {row['roas']:.1f}x — strong return. Consider increasing budget allocation here before scaling underperforming channels.")
    
        col1,col2 = st.columns(2)
        with col1:
            fig = px.bar(roi_df,x="channel_name",y=["total_spend","attributed_rev"],
                         barmode="group",title="Spend vs Attributed Revenue",
                         labels={"value":"Amount ($)","channel_name":"Channel"})
            fig.add_hline(y=0,line_color="gray")
            st.plotly_chart(fig,use_container_width=True)
        with col2:
            colors = ["#ef4444" if r<1.0 else "#22c55e" if r>2.0 else "#f59e0b"
                      for r in roi_df["roas"]]
            fig = go.Figure(go.Bar(x=roi_df["channel_name"],y=roi_df["roas"],
                                   marker_color=colors))
            fig.add_hline(y=1,line_dash="dash",line_color="red",annotation_text="Break Even")
            fig.update_layout(title="ROAS by Channel (red=losing money, green=strong)",
                              xaxis_title="Channel",yaxis_title="ROAS")
            st.plotly_chart(fig,use_container_width=True)
    
        daily = q("""
            SELECT fs.spend_date, ch.channel_name, SUM(fs.daily_spend) as spend
            FROM fact_spend fs JOIN dim_channel ch ON fs.channel_id=ch.channel_id
            WHERE fs.spend_date BETWEEN ? AND ?
            GROUP BY fs.spend_date, ch.channel_name ORDER BY fs.spend_date
        """, (start_d,end_d))
        if not daily.empty:
            fig = px.line(daily,x="spend_date",y="spend",color="channel_name",
                          title="Daily Spend Trend by Channel")
            st.plotly_chart(fig,use_container_width=True)
    
    # ══════════════════════════════════════════════════════════════════════════════
    # PAGE 3 — FULL FUNNEL
    # ══════════════════════════════════════════════════════════════════════════════
    elif page == PAGES[2]:
        st.title("Full Funnel Analysis")
        st.caption("Awareness → Engagement → Conversion · Source: GA4 · HubSpot · Segment")
    
        funnel_df = q("""
            SELECT COUNT(DISTINCT ft.customer_id) as prospects,
                   COUNT(DISTINCT CASE WHEN ft.touch_type IN ('Click','Email Click','SMS Click') THEN ft.customer_id END) as engaged,
                   COUNT(DISTINCT fc.customer_id) as converted,
                   COUNT(DISTINCT CASE WHEN fc.conversion_type='Trial Start' THEN fc.customer_id END) as trials,
                   COUNT(DISTINCT CASE WHEN fc.conversion_type='Subscription Start' THEN fc.customer_id END) as subscribers
            FROM fact_touchpoints ft
            LEFT JOIN fact_conversions fc ON ft.customer_id=fc.customer_id
            WHERE ft.touch_date BETWEEN ? AND ?
        """, (start_d,end_d))
    
        r = funnel_df.iloc[0]
        engaged_rate = round(r["engaged"]/r["prospects"]*100,1) if r["prospects"] else 0
        conv_rate    = round(r["converted"]/r["engaged"]*100,1) if r["engaged"] else 0
    
        if engaged_rate < 30:
            warn(f"Only <b>{engaged_rate}%</b> of reached prospects are engaging (clicking). Top-of-funnel creative or targeting may need refresh — high impression volume with low click-through wastes reach budget.")
        if conv_rate < 20:
            danger(f"Engaged-to-converted rate is <b>{conv_rate}%</b>. Over 80% of engaged prospects are dropping before converting — examine landing page experience, offer strength, and friction in the signup flow.")
    
        fig = go.Figure(go.Funnel(
            y=["Prospects Reached","Engaged","Converted","Trial Start","Paid Subscriber"],
            x=[r["prospects"],r["engaged"],r["converted"],r["trials"],r["subscribers"]],
            textinfo="value+percent initial",
            marker_color=["#1F4E79","#2E75B6","#4BACC6","#70AD47","#A9D18E"]
        ))
        fig.update_layout(title="Customer Acquisition Funnel")
        st.plotly_chart(fig,use_container_width=True)
    
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
            GROUP BY ch.channel_name, ch.source_platform ORDER BY cvr_pct DESC
        """, (start_d,end_d,start_d,end_d))
    
        avg_cvr = ch_funnel["cvr_pct"].mean()
        for _,row in ch_funnel.iterrows():
            if row["cvr_pct"] < avg_cvr*0.5:
                warn(f"<b>{row['channel_name']}</b> CVR of {row['cvr_pct']}% is less than half the channel average ({avg_cvr:.1f}%). High reach, low conversion — audit audience targeting and landing page alignment.")
    
        fig = px.bar(ch_funnel,x="channel_name",y="cvr_pct",color="source_platform",
                     title="Conversion Rate % by Channel",
                     labels={"cvr_pct":"CVR %","channel_name":"Channel"})
        fig.add_hline(y=avg_cvr,line_dash="dash",annotation_text=f"Avg {avg_cvr:.1f}%")
        st.plotly_chart(fig,use_container_width=True)
    
    # ══════════════════════════════════════════════════════════════════════════════
    # PAGE 4 — LTV & RETENTION
    # ══════════════════════════════════════════════════════════════════════════════
    elif page == PAGES[3]:
        st.title("LTV & Retention Analytics")
        st.caption("Source: HubSpot · Mixpanel — 30/60/90/180/365-day cohort windows")
    
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
            GROUP BY dc.acquisition_channel ORDER BY ltv_365 DESC
        """)
    
        seg_ltv = q("""
            SELECT dc.segment,
                   ROUND(SUM(CASE WHEN julianday(fo.order_date)-julianday(dc.first_seen_date)<=60
                       THEN fo.revenue ELSE 0 END)/NULLIF(COUNT(DISTINCT fo.customer_id),0),2) as ltv_60,
                   ROUND(SUM(CASE WHEN julianday(fo.order_date)-julianday(dc.first_seen_date)<=365
                       THEN fo.revenue ELSE 0 END)/NULLIF(COUNT(DISTINCT fo.customer_id),0),2) as ltv_365,
                   COUNT(DISTINCT fo.customer_id) as customers
            FROM fact_orders fo
            JOIN dim_customer dc ON fo.customer_id=dc.customer_id
            GROUP BY dc.segment
        """)
    
        if not ltv_df.empty:
            c1,c2,c3 = st.columns(3)
            best = ltv_df.iloc[0]
            worst = ltv_df.iloc[-1]
            c1.metric("Best 365-Day LTV Channel", best["acquisition_channel"],f"${best['ltv_365']:,.2f}")
            c2.metric("Worst 365-Day LTV Channel", worst["acquisition_channel"],f"${worst['ltv_365']:,.2f}")
            c3.metric("LTV Gap (Best vs Worst)", f"${best['ltv_365']-worst['ltv_365']:,.2f}")
    
            st.divider()
    
            # Detect channels where LTV flatlines between 60 and 90 days
            for _,row in ltv_df.iterrows():
                if row["ltv_90"] > 0 and (row["ltv_365"]-row["ltv_60"])/row["ltv_60"] < 0.15:
                    danger(f"<b>{row['acquisition_channel']}</b> LTV flatlines after 60 days — customers acquired here are churning early. Check whether acquisition targeting is pulling low-intent users.")
                if row["acquisition_channel"]=="Organic" and row["customers"] < ltv_df["customers"].mean()*0.5:
                    good(f"<b>Organic</b> has the highest LTV but lowest acquisition volume. This is an underinvested channel — increasing organic content investment could yield high-quality customers at lower CAC.")
    
            occ_row = seg_ltv[seg_ltv["segment"]=="Occasional"]
            if not occ_row.empty:
                occ = occ_row.iloc[0]
                if occ["ltv_365"] < occ["ltv_60"]*1.2:
                    danger(f"<b>Occasional segment</b> LTV flatlines after 60 days (60-day: ${occ['ltv_60']:,.2f} vs 365-day: ${occ['ltv_365']:,.2f}). These customers are not converting to habit — consider an engagement campaign at day 45-50 before churn occurs.")
    
        ltv_melt = ltv_df.melt(id_vars=["acquisition_channel"],
            value_vars=["ltv_30","ltv_60","ltv_90","ltv_180","ltv_365"],
            var_name="Window",value_name="LTV")
        ltv_melt["Window"] = ltv_melt["Window"].str.replace("ltv_","").apply(lambda x:f"{x}-Day")
        fig = px.line(ltv_melt,x="Window",y="LTV",color="acquisition_channel",
                      markers=True,title="LTV Curve by Acquisition Channel",
                      labels={"LTV":"Avg Revenue per Customer ($)"})
        st.plotly_chart(fig,use_container_width=True)
    
        churn_df = q("""
            SELECT dc.acquisition_channel,
                   COUNT(*) as total,
                   ROUND(SUM(CASE WHEN fs.status='Cancelled' THEN 1.0 ELSE 0 END)/COUNT(*)*100,1) as churn_rate
            FROM fact_subscriptions fs
            JOIN dim_customer dc ON fs.customer_id=dc.customer_id
            GROUP BY dc.acquisition_channel ORDER BY churn_rate DESC
        """)
    
        avg_churn = churn_df["churn_rate"].mean()
        for _,row in churn_df.iterrows():
            if row["churn_rate"] > avg_churn*1.5:
                danger(f"<b>{row['acquisition_channel']}</b> churn rate is {row['churn_rate']}% vs {avg_churn:.1f}% average — {row['churn_rate']/avg_churn:.1f}x the baseline. Acquisition quality problem: this channel may be attracting low-intent or price-sensitive users.")
    
        fig = px.bar(churn_df,x="acquisition_channel",y="churn_rate",
                     color="churn_rate",color_continuous_scale="RdYlGn_r",
                     title="Churn Rate by Acquisition Channel (%)")
        fig.add_hline(y=avg_churn,line_dash="dash",
                      annotation_text=f"Avg {avg_churn:.1f}%")
        st.plotly_chart(fig,use_container_width=True)
    
    # ══════════════════════════════════════════════════════════════════════════════
    # PAGE 5 — CART & REACTIVATION
    # ══════════════════════════════════════════════════════════════════════════════
    elif page == PAGES[4]:
        st.title("Cart Recovery & Reactivation Analytics")
        st.caption("Source: Klaviyo · Mixpanel — abandoned cart flows, win-back campaigns")
    
        cart_df = q("""
            SELECT event_type, COUNT(*) as events,
                   ROUND(AVG(cart_value),2) as avg_value
            FROM fact_cart_events WHERE event_date BETWEEN ? AND ?
            GROUP BY event_type
        """, (start_d,end_d))
    
        abandons = int(cart_df[cart_df["event_type"]=="Abandon"]["events"].sum()) if len(cart_df) else 0
        recovers = int(cart_df[cart_df["event_type"]=="Recover"]["events"].sum()) if len(cart_df) else 0
        rec_rate = round(recovers/abandons*100,1) if abandons else 0
    
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Cart Abandons", f"{abandons:,}")
        c2.metric("Carts Recovered", f"{recovers:,}")
        c3.metric("Recovery Rate", f"{rec_rate}%")
        avg_val = float(cart_df[cart_df["event_type"]=="Abandon"]["avg_value"].mean()) if len(cart_df) else 0
        c4.metric("Avg Abandoned Value", f"${avg_val:,.2f}")
    
        st.divider()
    
        offer_df = q("""
            SELECT offer_applied,
                   COUNT(*) as total,
                   SUM(CASE WHEN event_type='Recover' THEN 1 ELSE 0 END) as recoveries,
                   ROUND(SUM(CASE WHEN event_type='Recover' THEN 1.0 ELSE 0 END)/COUNT(*)*100,1) as rec_rate
            FROM fact_cart_events
            WHERE offer_applied IS NOT NULL AND event_date BETWEEN ? AND ?
            GROUP BY offer_applied ORDER BY rec_rate DESC
        """, (start_d,end_d))
    
        for _,row in offer_df.iterrows():
            if row["rec_rate"] < 15:
                danger(f"<b>'{row['offer_applied']}'</b> cart recovery offer has only {row['rec_rate']}% recovery rate — the lowest performing offer. This incentive is not motivating return. Recommend replacing with 'Free Month' which recovers at 3-4x this rate.")
            elif row["rec_rate"] > 35:
                good(f"<b>'{row['offer_applied']}'</b> is your strongest cart recovery offer at {row['rec_rate']}% — ensure this is the default offer in your Klaviyo abandoned cart flow.")
    
        col1,col2 = st.columns(2)
        with col1:
            fig = px.bar(offer_df,x="offer_applied",y="rec_rate",
                         color="rec_rate",color_continuous_scale="RdYlGn",
                         title="Cart Recovery Rate by Offer Type (%)",
                         labels={"rec_rate":"Recovery Rate %","offer_applied":"Offer"})
            st.plotly_chart(fig,use_container_width=True)
        with col2:
            ch_rec = q("""
                SELECT recovery_channel, COUNT(*) as recoveries
                FROM fact_cart_events
                WHERE event_type='Recover' AND recovery_channel IS NOT NULL
                AND event_date BETWEEN ? AND ?
                GROUP BY recovery_channel ORDER BY recoveries DESC
            """, (start_d,end_d))
            fig = px.pie(ch_rec,names="recovery_channel",values="recoveries",
                         title="Recovery Channel Mix")
            st.plotly_chart(fig,use_container_width=True)
    
        st.subheader("Reactivation Campaign Performance")
        react_df = q("""
            SELECT trigger_reason, offer_type,
                   COUNT(*) as sent,
                   SUM(CASE WHEN converted THEN 1 ELSE 0 END) as conversions,
                   ROUND(SUM(CASE WHEN converted THEN 1.0 ELSE 0 END)/COUNT(*)*100,1) as cvr,
                   ROUND(SUM(COALESCE(conversion_revenue,0)),2) as revenue_won_back
            FROM fact_reactivation_campaigns
            WHERE trigger_date BETWEEN ? AND ?
            GROUP BY trigger_reason, offer_type ORDER BY cvr DESC
        """, (start_d,end_d))
    
        churned_react = react_df[react_df["trigger_reason"]=="Churned"]
        atrisk_react  = react_df[react_df["trigger_reason"]=="At Risk"]
    
        if not churned_react.empty:
            avg_churned_cvr = churned_react["cvr"].mean()
            if avg_churned_cvr < 8:
                danger(f"<b>Win-back campaigns targeting Churned customers</b> are converting at only {avg_churned_cvr:.1f}%. This spend is largely wasted. Recommend pausing win-back for Churned and reallocating budget to At-Risk campaigns which convert at significantly higher rates.")
        if not atrisk_react.empty:
            avg_atrisk_cvr = atrisk_react["cvr"].mean()
            good(f"<b>At-Risk reactivation campaigns</b> convert at {avg_atrisk_cvr:.1f}% — intervening before churn is significantly more effective than win-back. Recommend earlier trigger logic (day 21 inactivity vs current thresholds).")
    
        c1,c2,c3 = st.columns(3)
        c1.metric("Campaigns Sent", f"{react_df['sent'].sum():,}")
        c2.metric("Customers Won Back", f"{react_df['conversions'].sum():,}")
        c3.metric("Revenue Won Back", f"${react_df['revenue_won_back'].sum():,.0f}")
    
        fig = px.scatter(react_df,x="offer_type",y="cvr",size="sent",color="trigger_reason",
                         title="Reactivation CVR by Offer Type & Trigger Reason",
                         labels={"cvr":"Conversion Rate %","offer_type":"Offer Type"})
        st.plotly_chart(fig,use_container_width=True)
    
    # ══════════════════════════════════════════════════════════════════════════════
    # PAGE 6 — BRAND & SHARE OF VOICE
    # ══════════════════════════════════════════════════════════════════════════════
    elif page == PAGES[5]:
        st.title("Brand Health & Share of Voice")
        st.caption("Non-paid analytics: organic reach, sentiment, NPS, branded search · Source: GA4 · HubSpot")
    
        brand_df = q("""
            SELECT bs.signal_date, ch.channel_name,
                   bs.share_of_voice, bs.organic_reach, bs.sentiment_score,
                   bs.mentions, bs.branded_searches, bs.nps_score
            FROM fact_brand_signals bs
            JOIN dim_channel ch ON bs.channel_id=ch.channel_id
            WHERE bs.signal_date BETWEEN ? AND ?
            ORDER BY bs.signal_date
        """, (start_d,end_d))
    
        if not brand_df.empty:
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Avg Share of Voice", f"{brand_df['share_of_voice'].mean()*100:.1f}%")
            c2.metric("Avg NPS Score", f"{brand_df['nps_score'].mean():.1f}")
            c3.metric("Avg Sentiment", f"{brand_df['sentiment_score'].mean():.2f}")
            c4.metric("Total Branded Searches", f"{brand_df['branded_searches'].sum():,}")
    
            nps_avg = brand_df["nps_score"].mean()
            if nps_avg < 40:
                danger(f"NPS averaging <b>{nps_avg:.1f}</b> — below the 'Good' threshold of 50. Customer satisfaction issues will compound churn. Recommend NPS deep-dive to identify detractor themes.")
            elif nps_avg > 60:
                good(f"NPS averaging <b>{nps_avg:.1f}</b> — strong promoter base. Consider activating referral program to convert brand satisfaction into acquisition channel.")
    
            st.divider()
            col1,col2 = st.columns(2)
            with col1:
                fig = px.line(brand_df,x="signal_date",y="share_of_voice",color="channel_name",
                              title="Share of Voice Over Time")
                st.plotly_chart(fig,use_container_width=True)
            with col2:
                fig = px.line(brand_df,x="signal_date",y="nps_score",color="channel_name",
                              title="NPS Score Trend")
                fig.add_hline(y=50,line_dash="dash",annotation_text="Good Threshold")
                st.plotly_chart(fig,use_container_width=True)
    
    # ══════════════════════════════════════════════════════════════════════════════

    elif page == PAGES[6]:
        st.title("Data Sources & Schema")
        st.caption("Simulated platform data — no real API connections · 14 tables · 95,000+ rows")
    
        platforms = {
            "GA4 (Google Analytics 4)": {
                "color":"#E37400","tables":["fact_touchpoints (Organic, Direct)","fact_brand_signals"],
                "what":"Web sessions, traffic sources, organic visits, goal completions, branded search volume"
            },
            "Google Ads": {
                "color":"#4285F4","tables":["fact_spend (Paid Search, Display)","fact_touchpoints (Paid Search)"],
                "what":"Keyword-level spend, impressions, clicks, CTR, CPC, CPM — daily grain"
            },
            "Meta Ads Manager": {
                "color":"#1877F2","tables":["fact_spend (Paid Social)","fact_touchpoints (Paid Social)"],
                "what":"Campaign and ad set spend, ROAS, reach, CPM by audience segment"
            },
            "HubSpot (CRM)": {
                "color":"#FF7A59","tables":["dim_customer","fact_conversions","fact_brand_signals (NPS)"],
                "what":"Contact lifecycle stages, deal pipeline, NPS surveys, form submissions"
            },
            "Klaviyo": {
                "color":"#22BC66","tables":["fact_touchpoints (Email, SMS)","fact_cart_events","fact_reactivation_campaigns"],
                "what":"Email/SMS sends, opens, clicks, abandoned cart flows, win-back sequences, offer redemptions"
            },
            "Segment (CDP)": {
                "color":"#52BD94","tables":["fact_attribution","fact_touchpoints (identity stitching)"],
                "what":"Cross-platform identity resolution, customer journey stitching across all sources"
            },
            "Mixpanel": {
                "color":"#7856FF","tables":["fact_touchpoints (In-App)","fact_subscriptions"],
                "what":"In-app events, feature usage, activity levels, session frequency — feeds at-risk detection"
            },
        }
    
        for platform,info in platforms.items():
            with st.expander(f"**{platform}**"):
                col1,col2 = st.columns([1,2])
                with col1:
                    st.markdown("**Tables fed:**")
                    for t in info["tables"]: st.markdown(f"- `{t}`")
                with col2:
                    st.markdown(f"**What it simulates:** {info['what']}")
    
        st.divider()
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
        counts["rows"] = counts["rows"].apply(lambda x:f"{x:,}")
        st.dataframe(counts.rename(columns={"tbl":"Table","rows":"Row Count"}),
                     use_container_width=True,hide_index=True)