# Marketing Attribution Intelligence Platform

> **A full-stack marketing analytics engineering project** — built by someone who spent 13 years inside marketing asking for this data, then went and built the infrastructure to produce it.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Claude API](https://img.shields.io/badge/Claude_API-191919?style=flat&logo=anthropic&logoColor=white)](https://anthropic.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat)](LICENSE)

---

## The Problem This Solves

Most marketing analytics projects stop at the dashboard. They show you what happened. They don't tell you what's broken, what it's costing you, or what to do about it.

This platform goes further. It simulates the full marketing data environment of a B2C subscription brand — across seven real-world platforms — and layers on top of it:

- **Five attribution models** compared side by side so you can see how budget recommendations change depending on which model you trust
- **Intentional data problems** baked in: channels with negative ROAS, acquisition sources with 2x average churn, offers that don't recover carts, reactivation campaigns wasting spend on already-churned customers
- **Inline analytical insights** on every page that read like a senior analyst in the room — not just observations, but specific actions
- **An AI recommendation engine** powered by the Claude API that runs live diagnostic queries against the data and produces a prioritized action plan with impact estimates, effort ratings, and owners

The goal: demonstrate what a marketing analytics engineer actually does — not just build a pretty dashboard, but understand the business well enough to know when the data is telling you something is wrong, and build the systems to surface it before anyone has to ask.

---

## Live Demo

🚀 **[marketing-attribution.streamlit.app](https://marketing-attribution.streamlit.app)**

---

## What's Inside

### 7 Analytical Views

| Page | What It Shows |
|------|---------------|
| 📊 Attribution Models | First Touch · Last Touch · Linear · Time Decay · U-Shaped — all five models side by side with channel-level comparison |
| 💰 Spend & ROI | Daily spend vs. attributed revenue by channel · ROAS · break-even flagging · underperforming channel alerts |
| 🔄 Full Funnel | Awareness → engagement → conversion funnel · CVR by channel · touches-to-convert distribution |
| 💎 LTV & Retention | 30/60/90/180/365-day LTV curves by acquisition channel · churn rate by source · segment LTV flatline detection |
| 🛒 Cart & Reactivation | Abandoned cart recovery by offer type · recovery channel mix · reactivation campaign CVR by trigger reason |
| 📣 Brand & Share of Voice | Weekly SoV · organic reach · NPS trend · sentiment score · branded search volume |
| 🗄️ Data Sources | Platform-to-table mapping · full schema with row counts |

### 🤖 AI Recommendations (Standalone)

Click **Run Full Analysis** in the sidebar. The platform pulls six live diagnostic queries, sends them to the Claude API, and returns a prioritized action plan — each recommendation includes a problem statement grounded in the data, a specific action, an estimated impact, effort level, and an owner (Media / CRM / Product / Leadership).

---

## Simulated Data Sources

The platform simulates data as if it were sourced from real marketing platforms — no actual API connections, but the schema, grain, and field names reflect how these systems actually produce data.

| Platform | What It Simulates |
|----------|-------------------|
| **GA4** | Web sessions, organic traffic, branded search, goal completions |
| **Google Ads** | Paid search + display spend at daily grain · CTR · CPC · CPM |
| **Meta Ads** | Paid social campaign spend · reach · frequency · ROAS |
| **HubSpot** | Contact lifecycle stages · NPS surveys · form submissions · deal pipeline |
| **Klaviyo** | Email/SMS sends · abandoned cart flows · win-back sequences · offer redemptions |
| **Segment (CDP)** | Cross-platform identity resolution · customer journey stitching · attribution model inputs |
| **Mixpanel** | In-app events · feature usage · activity levels · at-risk detection signals |

---

## Data Problems Baked In

Real marketing data is messy. This dataset reflects that.

| Problem | What to Look For |
|---------|-----------------|
| Display + Paid Social: ROAS < 1.0 | Spend & ROI page — bars turn red below break-even |
| Email acquisition: 2x churn rate vs. Organic | LTV & Retention — churn rate chart |
| Organic: highest LTV, lowest volume | LTV curve — flat line at the top with the smallest cohort |
| "10% Off" cart offer: 12% recovery rate | Cart & Reactivation — offer comparison bar |
| Win-back (Churned) reactivation: 4% CVR | Reactivation scatter — churned trigger at the bottom |
| Occasional segment: LTV flatlines at 60 days | LTV curve — segment line goes flat after 60-day window |

---

## Schema

14 tables · ~96,000 synthetic rows · 2023–2024

```
Dimensions
├── dim_customer       — 5,000 customers with acquisition channel, segment, lifecycle stage
├── dim_channel        — 10 channels mapped to source platforms
├── dim_campaign       — 80 campaigns with objectives and offer types
├── dim_product        — 5 subscription plans (Trial, Starter, Pro, Business, Add-on)
└── dim_date           — Full date spine 2023–2024

Facts
├── fact_touchpoints         — 40,000+ customer interactions across all channels
├── fact_conversions         — Conversion events with type, revenue, touches-to-convert
├── fact_spend               — Daily channel spend with impressions, clicks, CTR, CPC, CPM
├── fact_subscriptions       — Plan starts, upgrades, downgrades, cancellations with reasons
├── fact_orders              — Full order history for LTV calculation
├── fact_cart_events         — Abandon → recovery events with offer type and channel
├── fact_reactivation_campaigns — Win-back and at-risk campaigns with CVR by trigger
├── fact_brand_signals       — Weekly SoV, NPS, sentiment, branded search, organic reach
└── fact_attribution         — Pre-computed attribution credits for all 5 models per touchpoint
```

---

## Setup

```bash
# Clone
git clone https://github.com/BigZeeke/marketing-attribution.git
cd marketing-attribution

# Install dependencies
pip install -r requirements.txt

# Generate the database (~96,000 rows, ~30 seconds)
python generate_data.py

# Run the app
streamlit run app.py
```

### AI Recommendations Setup

Create `.streamlit/secrets.toml`:

```toml
ANTHROPIC_API_KEY = "sk-ant-your-key-here"
```

> The `.streamlit/secrets.toml` file is gitignored. Never commit your API key.

---

## Tech Stack

| Layer | Tools |
|-------|-------|
| Data generation | Python · Faker · SQLite |
| SQL | SQLite · window functions · CTEs · multi-table joins · CASE aggregations |
| Application | Streamlit · Plotly · pandas |
| AI layer | Anthropic Claude API · structured JSON output · prompt engineering |
| Schema design | Star schema · dim/fact architecture · 4-source-system simulation |

---

## About

Built by **Steve Lopez** — Marketing Analytics Engineer with 13 years inside marketing and the technical depth to build the data infrastructure that powers it.

- 🌐 [LinkedIn](https://linkedin.com/in/stevelopezenterprise)
- 💻 [GitHub](https://github.com/BigZeeke)
- 📊 [Automotive Pricing Analytics](https://pricing-analytics.streamlit.app)
- 🤖 [Marketing Analytics Assistant](https://marketing-analytics-assistant.streamlit.app)
