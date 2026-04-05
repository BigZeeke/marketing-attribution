"""
generate_data.py
================
Synthetic data generator for B2C Subscription Brand Marketing Attribution Platform.
Simulates data as if sourced from: GA4, HubSpot, Meta Ads, Google Ads, Klaviyo,
Segment (CDP), and Mixpanel — without connecting to any real platform.

Generates ~75,000 rows across 14 tables. Runtime: ~30 seconds.
"""

import sqlite3
import random
import math
from datetime import date, datetime, timedelta
from faker import Faker

fake = Faker()
random.seed(42)

DB_PATH = "/home/claude/mktg_attribution/marketing_attribution.db"

# ── CONFIG ────────────────────────────────────────────────────────────────────
START_DATE = date(2023, 1, 1)
END_DATE   = date(2024, 12, 31)
N_CUSTOMERS = 5000
N_CAMPAIGNS = 80

CHANNELS = [
    (1, "Paid Search",   "Paid",     "Performance", "Google Ads"),
    (2, "Paid Social",   "Paid",     "Performance", "Meta Ads"),
    (3, "Email",         "Non-Paid", "Retention",   "Klaviyo"),
    (4, "Organic",       "Non-Paid", "Brand",       "GA4"),
    (5, "Direct",        "Non-Paid", "Brand",       "GA4"),
    (6, "Referral",      "Non-Paid", "Performance", "GA4"),
    (7, "Display",       "Paid",     "Brand",       "Google Ads"),
    (8, "Paid Social",   "Paid",     "Performance", "Meta Ads"),
    (9, "SMS",           "Non-Paid", "Retention",   "Klaviyo"),
    (10,"In-App",        "Non-Paid", "Retention",   "Mixpanel"),
]

SEGMENTS     = ["High Value","Mid Tier","Occasional","At Risk","Churned"]
REGIONS      = ["Northeast","Southeast","Midwest","West","Southwest","Pacific"]
DEVICES      = ["Mobile","Desktop","Tablet"]
AGE_GROUPS   = ["18-24","25-34","35-44","45-54","55+"]
LIFECYCLE    = ["Prospect","Trial","Active","At Risk","Churned","Reactivated"]
OBJECTIVES   = ["Awareness","Consideration","Conversion","Retention","Reactivation"]
OFFER_TYPES  = ["None","Discount","Free Trial","Incentive","Win-back"]
PLAN_TYPES   = ["Monthly","Annual","Trial"]
TOUCH_TYPES  = ["Impression","Click","Email Open","Email Click","Organic Visit","Direct Visit","SMS Click","In-App Event"]
CANCEL_REASONS = ["Price","Found alternative","Not using enough","Missing features","Financial reasons",""]

PRODUCTS = [
    (1, "Starter Plan",    "Subscription", "Monthly", 9.99,  99.00),
    (2, "Pro Plan",        "Subscription", "Monthly", 19.99, 199.00),
    (3, "Business Plan",   "Subscription", "Annual",  49.99, 499.00),
    (4, "Free Trial",      "Trial",        "Trial",   0.00,  0.00),
    (5, "Add-on Feature",  "Add-on",       "Monthly", 4.99,  49.00),
]

def rand_date(start=START_DATE, end=END_DATE):
    return start + timedelta(days=random.randint(0, (end - start).days))

def rand_datetime(d):
    return datetime(d.year, d.month, d.day, random.randint(6,23), random.randint(0,59))

def date_range(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)

def build_date_dim():
    rows = []
    d = START_DATE
    did = 1
    while d <= END_DATE:
        rows.append((
            did, d.isoformat(), d.year,
            (d.month-1)//3+1, d.month,
            d.strftime("%B"), d.isocalendar()[1],
            d.weekday(), d.strftime("%A"),
            d.weekday() >= 5
        ))
        d += timedelta(days=1)
        did += 1
    return rows

def build_campaigns():
    rows = []
    names_used = set()
    for i in range(1, N_CAMPAIGNS+1):
        ch   = random.choice(CHANNELS)
        obj  = random.choice(OBJECTIVES)
        offer= random.choice(OFFER_TYPES)
        seg  = random.choice(SEGMENTS + ["All"])
        sd   = rand_date(START_DATE, date(2024,6,1))
        ed   = sd + timedelta(days=random.randint(14,120))
        name = f"{ch[0+4]}_{obj}_{sd.strftime('%Y%m')}_{i}"
        rows.append((i, ch[0], name, obj, sd.isoformat(),
                     min(ed,END_DATE).isoformat(), seg, offer))
    return rows

def build_customers():
    rows = []
    for i in range(1, N_CUSTOMERS+1):
        ch   = random.choice(CHANNELS)
        acq  = rand_date(START_DATE, date(2024,6,1))
        seg  = random.choices(SEGMENTS, weights=[20,35,25,12,8])[0]
        life = random.choice(LIFECYCLE)
        rows.append((
            i, acq.isoformat(), ch[1],
            f"{ch[4]}_Campaign_{random.randint(1,N_CAMPAIGNS)}",
            seg, random.choice(REGIONS),
            random.choice(DEVICES), random.choice(AGE_GROUPS), life
        ))
    return rows

def build_touchpoints(customers, campaigns):
    rows = []
    tid = 1
    cmp_map = {c[0]:c for c in campaigns}
    for cust in customers:
        cid      = cust[0]
        acq_date = date.fromisoformat(cust[1])
        n_touches = random.randint(1, 15)
        touches  = sorted([rand_date(acq_date, min(acq_date+timedelta(60), END_DATE))
                           for _ in range(n_touches)])
        for seq, td in enumerate(touches, 1):
            ch    = random.choice(CHANNELS)
            camp  = random.choice(campaigns)
            ttype = random.choice(TOUCH_TYPES)
            is_paid = ch[2] == "Paid"
            rows.append((
                tid, cid, ch[0], camp[0],
                td.isoformat(), rand_datetime(td).isoformat(),
                ttype, fake.uuid4()[:8],
                random.choice(DEVICES), is_paid, seq
            ))
            tid += 1
    return rows

def build_conversions(customers, campaigns, touchpoints):
    rows = []
    cid_touches = {}
    for t in touchpoints:
        cid_touches.setdefault(t[1],[]).append(t)

    conv_id = 1
    for cust in customers:
        cid = cust[0]
        if random.random() < 0.65:
            touches = cid_touches.get(cid,[])
            if not touches:
                continue
            last_touch = date.fromisoformat(sorted(touches, key=lambda x:x[4])[-1][4])
            conv_date  = last_touch + timedelta(days=random.randint(0,7))
            if conv_date > END_DATE:
                continue
            camp  = random.choice(campaigns)
            prod  = random.choice(PRODUCTS[:3])
            rev   = prod[4] if random.random() < 0.7 else prod[5]
            ctype = random.choices(
                ["Trial Start","Subscription Start","Upsell","Reactivation"],
                weights=[30,50,15,5])[0]
            rows.append((
                conv_id, cid, camp[0], conv_date.isoformat(),
                ctype, round(rev,2), prod[0],
                conv_id == 1, random.randint(1,30), len(touches)
            ))
            conv_id += 1
    return rows

def build_spend(campaigns):
    rows = []
    sid = 1
    for camp in campaigns:
        sd = date.fromisoformat(camp[4])
        ed = date.fromisoformat(camp[5])
        ch_id = camp[1]
        ch = next((c for c in CHANNELS if c[0]==ch_id), CHANNELS[0])
        if ch[2] != "Paid":
            continue
        base_spend = random.uniform(50, 2000)
        for d in date_range(sd, min(ed, END_DATE)):
            spend   = round(base_spend * random.uniform(0.7,1.3), 2)
            impr    = int(spend * random.uniform(100,500))
            clicks  = int(impr * random.uniform(0.01,0.05))
            ctr     = round(clicks/impr if impr else 0, 4)
            cpc     = round(spend/clicks if clicks else 0, 2)
            cpm     = round((spend/impr)*1000 if impr else 0, 2)
            rows.append((sid, ch_id, camp[0], d.isoformat(),
                         spend, impr, clicks, ctr, cpc, cpm))
            sid += 1
    return rows

def build_subscriptions(customers, conversions):
    rows = []
    sub_id = 1
    conv_map = {c[1]:c for c in conversions}
    for cust in customers:
        cid  = cust[0]
        conv = conv_map.get(cid)
        if not conv:
            continue
        start = date.fromisoformat(conv[3])
        prod  = PRODUCTS[conv[6]-1]
        plan  = prod[3]
        mrr   = round(prod[4],2)
        status= random.choices(
            ["Active","Cancelled","Paused","Upgraded","Downgraded"],
            weights=[55,25,5,10,5])[0]
        end   = None if status=="Active" else (
            start+timedelta(days=random.randint(30,365))).isoformat()
        rows.append((sub_id, cid, prod[0], start.isoformat(), end,
                     status, plan, mrr, "New", start.isoformat(),
                     random.choice(CANCEL_REASONS) if status=="Cancelled" else ""))
        sub_id += 1
    return rows

def build_orders(customers, conversions):
    rows = []
    oid = 1
    conv_map = {c[1]:c for c in conversions}
    for cust in customers:
        cid  = cust[0]
        conv = conv_map.get(cid)
        if not conv:
            continue
        start = date.fromisoformat(conv[3])
        n_orders = random.randint(1, 12)
        prod  = PRODUCTS[conv[6]-1]
        for n in range(1, n_orders+1):
            od  = start + timedelta(days=30*(n-1)+random.randint(0,5))
            if od > END_DATE:
                break
            rev = round(prod[4] * random.uniform(0.9,1.1), 2)
            rows.append((oid, cid, prod[0], od.isoformat(),
                         rev, n>1, n))
            oid += 1
    return rows

def build_cart_events(customers, campaigns):
    rows = []
    ceid = 1
    for cust in customers:
        if random.random() < 0.40:
            cid  = cust[0]
            ed   = rand_date(date.fromisoformat(cust[1]), END_DATE)
            prod = random.choice(PRODUCTS[:3])
            val  = round(prod[4]*random.uniform(1,3),2)
            evtype = "Abandon"
            recovered = random.random() < 0.35
            rec_ch = random.choice(["Email","SMS","Paid Social","Direct","None"])
            rec_days = random.randint(1,7) if recovered else None
            offer = random.choice(["10% Off","Free Month","None","$5 Credit"]) if recovered else None
            camp = random.choice(campaigns)
            rows.append((ceid, cid, prod[0], camp[0],
                         ed.isoformat(), rand_datetime(ed).isoformat(),
                         evtype, val,
                         rec_ch if recovered else None,
                         rec_days, offer))
            ceid += 1
            if recovered:
                rd = ed + timedelta(days=rec_days)
                if rd <= END_DATE:
                    rows.append((ceid, cid, prod[0], camp[0],
                                 rd.isoformat(), rand_datetime(rd).isoformat(),
                                 "Recover", val, rec_ch, rec_days, offer))
                    ceid += 1
    return rows

def build_reactivation(customers, campaigns):
    rows = []
    rid = 1
    for cust in customers:
        if cust[8] in ("Churned","At Risk") and random.random() < 0.60:
            cid    = cust[0]
            tdate  = rand_date(date.fromisoformat(cust[1]), END_DATE)
            camp   = random.choice(campaigns)
            ch     = random.choice(CHANNELS)
            reason = random.choice(["Churned","At Risk","Low Activity","Abandoned Cart"])
            days_i = random.randint(14,180)
            offer  = random.choice(["Discount","Free Month","Feature Unlock","None"])
            oval   = round(random.uniform(5,50),2) if offer!="None" else 0
            sent   = tdate + timedelta(days=random.randint(1,3))
            conv   = random.random() < 0.28
            cdate  = (sent+timedelta(days=random.randint(1,14))).isoformat() if conv else None
            crev   = round(random.uniform(9.99,49.99),2) if conv else None
            rows.append((rid, cid, camp[0], ch[0],
                         tdate.isoformat(), reason, days_i,
                         offer, oval, sent.isoformat(), conv,
                         cdate, crev))
            rid += 1
    return rows

def build_brand_signals(campaigns):
    rows = []
    sid = 1
    for d in date_range(START_DATE, END_DATE):
        if d.weekday() == 0:  # weekly on Mondays
            for ch in CHANNELS:
                if ch[3] == "Brand":
                    sov    = round(random.uniform(0.05,0.35),4)
                    reach  = random.randint(5000,150000)
                    senti  = round(random.uniform(0.2,0.9),3)
                    ment   = random.randint(50,2000)
                    bsrch  = random.randint(1000,50000)
                    nps    = round(random.uniform(20,75),2)
                    nps_r  = random.randint(50,500)
                    rows.append((sid, d.isoformat(), ch[0],
                                 sov, reach, senti, ment, bsrch, nps, nps_r))
                    sid += 1
    return rows

def build_attribution(conversions, touchpoints):
    rows = []
    aid = 1
    tp_map = {}
    for t in touchpoints:
        tp_map.setdefault(t[1],[]).append(t)

    for conv in conversions:
        cid     = conv[1]
        rev     = float(conv[5])
        touches = sorted(tp_map.get(cid,[]), key=lambda x:x[4])
        if not touches:
            continue
        n = len(touches)
        for i, t in enumerate(touches):
            seq = i+1
            # First touch
            ft = 1.0 if seq==1 else 0.0
            # Last touch
            lt = 1.0 if seq==n else 0.0
            # Linear
            lin = round(1/n, 6)
            # Time decay — more credit to recent touches
            weights = [math.exp(0.3*(j+1)) for j in range(n)]
            td_w = round(weights[i]/sum(weights), 6)
            # U-shaped — 40% first, 40% last, 20% middle
            if n == 1:
                u = 1.0
            elif n == 2:
                u = 0.5
            else:
                mid_w = 0.20/(n-2) if n>2 else 0
                if seq == 1:   u = 0.40
                elif seq == n: u = 0.40
                else:          u = round(mid_w, 6)

            rows.append((aid, conv[0], t[0], cid, t[2], t[3],
                         t[4], seq, n, round(rev,2),
                         round(ft,6), round(lt,6),
                         round(lin,6), round(td_w,6), round(u,6)))
            aid += 1
    return rows

def main():
    print("Building synthetic marketing attribution database...")
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()
    c.executescript(open("/home/claude/mktg_attribution_schema.sql").read())

    print("  Generating dimensions...")
    c.executemany("INSERT INTO dim_channel VALUES (?,?,?,?,?)",
                  [(ch[0],ch[1],ch[2],ch[3],ch[4]) for ch in CHANNELS])

    date_rows = build_date_dim()
    c.executemany("INSERT INTO dim_date VALUES (?,?,?,?,?,?,?,?,?,?)", date_rows)
    print(f"    dim_date: {len(date_rows)} rows")

    for p in PRODUCTS:
        c.execute("INSERT INTO dim_product VALUES (?,?,?,?,?,?)", p)

    print("  Generating campaigns...")
    campaigns = build_campaigns()
    c.executemany("INSERT INTO dim_campaign VALUES (?,?,?,?,?,?,?,?)", campaigns)
    print(f"    dim_campaign: {len(campaigns)} rows")

    print("  Generating customers...")
    customers = build_customers()
    c.executemany("INSERT INTO dim_customer VALUES (?,?,?,?,?,?,?,?,?)", customers)
    print(f"    dim_customer: {len(customers)} rows")

    print("  Generating touchpoints...")
    touchpoints = build_touchpoints(customers, campaigns)
    c.executemany("INSERT INTO fact_touchpoints VALUES (?,?,?,?,?,?,?,?,?,?,?)", touchpoints)
    print(f"    fact_touchpoints: {len(touchpoints)} rows")

    print("  Generating conversions...")
    conversions = build_conversions(customers, campaigns, touchpoints)
    c.executemany("INSERT INTO fact_conversions VALUES (?,?,?,?,?,?,?,?,?,?)", conversions)
    print(f"    fact_conversions: {len(conversions)} rows")

    print("  Generating spend...")
    spend = build_spend(campaigns)
    c.executemany("INSERT INTO fact_spend VALUES (?,?,?,?,?,?,?,?,?,?)", spend)
    print(f"    fact_spend: {len(spend)} rows")

    print("  Generating subscriptions...")
    subscriptions = build_subscriptions(customers, conversions)
    c.executemany("INSERT INTO fact_subscriptions VALUES (?,?,?,?,?,?,?,?,?,?,?)", subscriptions)
    print(f"    fact_subscriptions: {len(subscriptions)} rows")

    print("  Generating orders...")
    orders = build_orders(customers, conversions)
    c.executemany("INSERT INTO fact_orders VALUES (?,?,?,?,?,?,?)", orders)
    print(f"    fact_orders: {len(orders)} rows")

    print("  Generating cart events...")
    cart = build_cart_events(customers, campaigns)
    c.executemany("INSERT INTO fact_cart_events VALUES (?,?,?,?,?,?,?,?,?,?,?)", cart)
    print(f"    fact_cart_events: {len(cart)} rows")

    print("  Generating reactivation campaigns...")
    react = build_reactivation(customers, campaigns)
    c.executemany("INSERT INTO fact_reactivation_campaigns VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", react)
    print(f"    fact_reactivation_campaigns: {len(react)} rows")

    print("  Generating brand signals...")
    brand = build_brand_signals(campaigns)
    c.executemany("INSERT INTO fact_brand_signals VALUES (?,?,?,?,?,?,?,?,?,?)", brand)
    print(f"    fact_brand_signals: {len(brand)} rows")

    print("  Generating attribution model outputs...")
    attribution = build_attribution(conversions, touchpoints)
    c.executemany("INSERT INTO fact_attribution VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", attribution)
    print(f"    fact_attribution: {len(attribution)} rows")

    conn.commit()
    total = sum([len(date_rows), len(campaigns), len(customers), len(touchpoints),
                 len(conversions), len(spend), len(subscriptions), len(orders),
                 len(cart), len(react), len(brand), len(attribution)])
    print(f"\n✓ Database ready: {DB_PATH}")
    print(f"  Total rows: {total:,}")
    conn.close()

if __name__ == "__main__":
    main()
