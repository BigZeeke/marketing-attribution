"""
generate_data_v2.py — Realistic messy B2C marketing data
Intentional problems baked in:
  - Display + Paid Social: high spend, ROAS < 1.0
  - Email acquisition: high churn rate (2x organic)
  - Organic: best LTV but underinvested
  - "10% Off" cart offer: lowest recovery rate
  - Win-back reactivation for Churned: near-zero CVR
  - Occasional segment: LTV flatlines at 60 days
"""
import sqlite3, random, math
from datetime import date, datetime, timedelta
from faker import Faker

fake = Faker()
random.seed(42)

DB_PATH = "marketing_attribution.db"
START_DATE = date(2023, 1, 1)
END_DATE   = date(2024, 12, 31)
N_CUSTOMERS = 5000
N_CAMPAIGNS = 80

CHANNELS = [
    (1,  "Paid Search",  "Paid",     "Performance", "Google Ads"),
    (2,  "Paid Social",  "Paid",     "Performance", "Meta Ads"),
    (3,  "Email",        "Non-Paid", "Retention",   "Klaviyo"),
    (4,  "Organic",      "Non-Paid", "Brand",       "GA4"),
    (5,  "Direct",       "Non-Paid", "Brand",       "GA4"),
    (6,  "Referral",     "Non-Paid", "Performance", "GA4"),
    (7,  "Display",      "Paid",     "Brand",       "Google Ads"),
    (8,  "SMS",          "Non-Paid", "Retention",   "Klaviyo"),
    (9,  "In-App",       "Non-Paid", "Retention",   "Mixpanel"),
    (10, "Affiliate",    "Paid",     "Performance", "GA4"),
]

# Channel spend multipliers — Display and Paid Social spend a lot but convert poorly
CHANNEL_SPEND_BASE = {
    1: 800,   # Paid Search — decent ROAS
    2: 1800,  # Paid Social — high spend, poor ROAS (PROBLEM)
    7: 1500,  # Display — high spend, poor ROAS (PROBLEM)
    10: 400,  # Affiliate — moderate
}

# Channel conversion rates — Organic best, Display worst
CHANNEL_CVR = {
    1: 0.72,  # Paid Search
    2: 0.45,  # Paid Social — low
    3: 0.60,  # Email
    4: 0.85,  # Organic — best
    5: 0.70,  # Direct
    6: 0.68,  # Referral
    7: 0.28,  # Display — worst (PROBLEM)
    8: 0.55,  # SMS
    9: 0.65,  # In-App
    10: 0.50, # Affiliate
}

# Channel churn rates — Email acquisition churns 2x organic
CHANNEL_CHURN = {
    "Paid Search":  0.22,
    "Paid Social":  0.28,
    "Email":        0.42,  # PROBLEM — 2x organic
    "Organic":      0.18,  # best retention
    "Direct":       0.20,
    "Referral":     0.24,
    "Display":      0.35,
    "SMS":          0.30,
    "In-App":       0.22,
    "Affiliate":    0.32,
}

# Segment LTV multipliers — Occasional flatlines at 60 days
SEGMENT_LTV = {
    "High Value":  1.8,
    "Mid Tier":    1.0,
    "Occasional":  0.3,   # PROBLEM — flatlines early
    "At Risk":     0.5,
    "Churned":     0.1,
}

SEGMENTS  = ["High Value","Mid Tier","Occasional","At Risk","Churned"]
REGIONS   = ["Northeast","Southeast","Midwest","West","Southwest","Pacific"]
DEVICES   = ["Mobile","Desktop","Tablet"]
AGE_GROUPS= ["18-24","25-34","35-44","45-54","55+"]
LIFECYCLE = ["Prospect","Trial","Active","At Risk","Churned","Reactivated"]

PRODUCTS = [
    (1, "Starter Plan",   "Subscription", "Monthly", 9.99,  99.00),
    (2, "Pro Plan",       "Subscription", "Monthly", 19.99, 199.00),
    (3, "Business Plan",  "Subscription", "Annual",  49.99, 499.00),
    (4, "Free Trial",     "Trial",        "Trial",   0.00,  0.00),
    (5, "Add-on Feature", "Add-on",       "Monthly", 4.99,  49.00),
]

OBJECTIVES  = ["Awareness","Consideration","Conversion","Retention","Reactivation"]
OFFER_TYPES = ["None","Discount","Free Trial","Incentive","Win-back"]
TOUCH_TYPES = ["Impression","Click","Email Open","Email Click","Organic Visit",
               "Direct Visit","SMS Click","In-App Event"]
CANCEL_REASONS = ["Price","Found alternative","Not using enough","Missing features","Financial reasons",""]

def rd(start=START_DATE, end=END_DATE):
    return start + timedelta(days=random.randint(0,(end-start).days))

def rdt(d):
    return datetime(d.year,d.month,d.day,random.randint(6,23),random.randint(0,59))

def date_range(s,e):
    d=s
    while d<=e:
        yield d
        d+=timedelta(days=1)

def build_date_dim():
    rows,d,did=[],START_DATE,1
    while d<=END_DATE:
        rows.append((did,d.isoformat(),d.year,(d.month-1)//3+1,d.month,
                     d.strftime("%B"),d.isocalendar()[1],d.weekday(),
                     d.strftime("%A"),d.weekday()>=5))
        d+=timedelta(days=1); did+=1
    return rows

def build_campaigns():
    rows=[]
    for i in range(1,N_CAMPAIGNS+1):
        ch=random.choice(CHANNELS)
        obj=random.choice(OBJECTIVES)
        offer=random.choice(OFFER_TYPES)
        seg=random.choice(SEGMENTS+["All"])
        sd=rd(START_DATE,date(2024,6,1))
        ed=sd+timedelta(days=random.randint(14,120))
        name=f"{ch[4]}_{obj}_{sd.strftime('%Y%m')}_{i}"
        rows.append((i,ch[0],name,obj,sd.isoformat(),min(ed,END_DATE).isoformat(),seg,offer))
    return rows

def build_customers():
    rows=[]
    for i in range(1,N_CUSTOMERS+1):
        ch=random.choice(CHANNELS)
        acq=rd(START_DATE,date(2024,6,1))
        # Weight Organic lower volume but keep it present
        seg=random.choices(SEGMENTS,weights=[20,35,25,12,8])[0]
        life=random.choice(LIFECYCLE)
        rows.append((i,acq.isoformat(),ch[1],
                     f"{ch[4]}_Campaign_{random.randint(1,N_CAMPAIGNS)}",
                     seg,random.choice(REGIONS),
                     random.choice(DEVICES),random.choice(AGE_GROUPS),life))
    return rows

def build_touchpoints(customers,campaigns):
    rows=[]; tid=1
    for cust in customers:
        cid=cust[0]
        acq=date.fromisoformat(cust[1])
        n=random.randint(1,15)
        touches=sorted([rd(acq,min(acq+timedelta(60),END_DATE)) for _ in range(n)])
        for seq,td in enumerate(touches,1):
            ch=random.choice(CHANNELS)
            camp=random.choice(campaigns)
            ttype=random.choice(TOUCH_TYPES)
            rows.append((tid,cid,ch[0],camp[0],td.isoformat(),rdt(td).isoformat(),
                         ttype,fake.uuid4()[:8],random.choice(DEVICES),ch[2]=="Paid",seq))
            tid+=1
    return rows

def build_conversions(customers,campaigns,touchpoints):
    rows=[]; conv_id=1
    cid_touches={}
    for t in touchpoints:
        cid_touches.setdefault(t[1],[]).append(t)
    for cust in customers:
        cid=cust[0]
        acq_channel=cust[2]
        # Find channel id for CVR lookup
        ch_match=next((c for c in CHANNELS if c[1]==acq_channel),CHANNELS[0])
        cvr=CHANNEL_CVR.get(ch_match[0],0.60)
        if random.random()<cvr:
            touches=cid_touches.get(cid,[])
            if not touches: continue
            last=date.fromisoformat(sorted(touches,key=lambda x:x[4])[-1][4])
            conv_date=last+timedelta(days=random.randint(0,7))
            if conv_date>END_DATE: continue
            camp=random.choice(campaigns)
            prod=random.choice(PRODUCTS[:3])
            rev=prod[4] if random.random()<0.7 else prod[5]
            ctype=random.choices(["Trial Start","Subscription Start","Upsell","Reactivation"],
                                 weights=[30,50,15,5])[0]
            rows.append((conv_id,cid,camp[0],conv_date.isoformat(),ctype,
                         round(rev,2),prod[0],conv_id==1,
                         random.randint(1,30),len(touches)))
            conv_id+=1
    return rows

def build_spend(campaigns):
    rows=[]; sid=1
    for camp in campaigns:
        sd=date.fromisoformat(camp[4])
        ed=date.fromisoformat(camp[5])
        ch_id=camp[1]
        ch=next((c for c in CHANNELS if c[0]==ch_id),CHANNELS[0])
        if ch[2]!="Paid": continue
        base=CHANNEL_SPEND_BASE.get(ch_id,500)*random.uniform(0.8,1.2)
        for d in date_range(sd,min(ed,END_DATE)):
            spend=round(base*random.uniform(0.7,1.3),2)
            impr=int(spend*random.uniform(100,500))
            clicks=int(impr*random.uniform(0.01,0.05))
            ctr=round(clicks/impr if impr else 0,4)
            cpc=round(spend/clicks if clicks else 0,2)
            cpm=round((spend/impr)*1000 if impr else 0,2)
            rows.append((sid,ch_id,camp[0],d.isoformat(),spend,impr,clicks,ctr,cpc,cpm))
            sid+=1
    return rows

def build_subscriptions(customers,conversions):
    rows=[]; sub_id=1
    conv_map={c[1]:c for c in conversions}
    for cust in customers:
        cid=cust[0]; acq_ch=cust[2]
        conv=conv_map.get(cid)
        if not conv: continue
        start=date.fromisoformat(conv[3])
        prod=PRODUCTS[conv[6]-1]
        plan=prod[3]; mrr=round(prod[4],2)
        # Churn rate based on acquisition channel
        churn_rate=CHANNEL_CHURN.get(acq_ch,0.25)
        status=random.choices(["Active","Cancelled","Paused","Upgraded","Downgraded"],
                              weights=[max(5,55-int(churn_rate*100)),
                                       int(churn_rate*100),5,10,5])[0]
        end=None if status=="Active" else (start+timedelta(days=random.randint(30,365))).isoformat()
        rows.append((sub_id,cid,prod[0],start.isoformat(),end,status,plan,mrr,
                     "New",start.isoformat(),
                     random.choice(CANCEL_REASONS) if status=="Cancelled" else ""))
        sub_id+=1
    return rows

def build_orders(customers,conversions):
    rows=[]; oid=1
    conv_map={c[1]:c for c in conversions}
    for cust in customers:
        cid=cust[0]; seg=cust[4]
        conv=conv_map.get(cid)
        if not conv: continue
        start=date.fromisoformat(conv[3])
        prod=PRODUCTS[conv[6]-1]
        ltv_mult=SEGMENT_LTV.get(seg,1.0)
        # Occasional segment: few orders, stop after 60 days
        max_days=60 if seg=="Occasional" else 365
        n_orders=max(1,int(random.randint(1,12)*ltv_mult))
        for n in range(1,n_orders+1):
            od=start+timedelta(days=30*(n-1)+random.randint(0,5))
            if od>END_DATE or (od-start).days>max_days: break
            rev=round(prod[4]*random.uniform(0.9,1.1)*ltv_mult,2)
            rows.append((oid,cid,prod[0],od.isoformat(),rev,n>1,n))
            oid+=1
    return rows

def build_cart_events(customers,campaigns):
    rows=[]; ceid=1
    # "10% Off" has lowest recovery rate intentionally
    OFFER_RECOVERY_RATE={
        "10% Off":   0.12,  # PROBLEM — worst offer
        "Free Month":0.42,
        "$5 Credit": 0.35,
        "None":      0.18,
    }
    for cust in customers:
        if random.random()<0.40:
            cid=cust[0]
            ed=rd(date.fromisoformat(cust[1]),END_DATE)
            prod=random.choice(PRODUCTS[:3])
            val=round(prod[4]*random.uniform(1,3),2)
            offer=random.choice(list(OFFER_RECOVERY_RATE.keys()))
            rec_rate=OFFER_RECOVERY_RATE[offer]
            recovered=random.random()<rec_rate
            rec_ch=random.choice(["Email","SMS","Paid Social","Direct"])
            rec_days=random.randint(1,7) if recovered else None
            camp=random.choice(campaigns)
            rows.append((ceid,cid,prod[0],camp[0],ed.isoformat(),rdt(ed).isoformat(),
                         "Abandon",val,rec_ch if recovered else None,rec_days,offer))
            ceid+=1
            if recovered:
                rdate=ed+timedelta(days=rec_days)
                if rdate<=END_DATE:
                    rows.append((ceid,cid,prod[0],camp[0],rdate.isoformat(),
                                 rdt(rdate).isoformat(),"Recover",val,rec_ch,rec_days,offer))
                    ceid+=1
    return rows

def build_reactivation(customers,campaigns):
    rows=[]; rid=1
    # Win-back for Churned has near-zero CVR — PROBLEM
    TRIGGER_CVR={
        "Churned":        0.04,  # PROBLEM — wasted spend
        "At Risk":        0.32,
        "Low Activity":   0.28,
        "Abandoned Cart": 0.35,
    }
    for cust in customers:
        if cust[8] in ("Churned","At Risk") and random.random()<0.60:
            cid=cust[0]
            tdate=rd(date.fromisoformat(cust[1]),END_DATE)
            camp=random.choice(campaigns)
            ch=random.choice(CHANNELS)
            reason=random.choices(
                ["Churned","At Risk","Low Activity","Abandoned Cart"],
                weights=[30,30,25,15])[0]
            days_i=random.randint(14,180)
            offer=random.choice(["Discount","Free Month","Feature Unlock","None"])
            oval=round(random.uniform(5,50),2) if offer!="None" else 0
            sent=tdate+timedelta(days=random.randint(1,3))
            cvr=TRIGGER_CVR.get(reason,0.25)
            conv=random.random()<cvr
            cdate=(sent+timedelta(days=random.randint(1,14))).isoformat() if conv else None
            crev=round(random.uniform(9.99,49.99),2) if conv else None
            rows.append((rid,cid,camp[0],ch[0],tdate.isoformat(),reason,days_i,
                         offer,oval,sent.isoformat(),conv,cdate,crev))
            rid+=1
    return rows

def build_brand_signals(campaigns):
    rows=[]; sid=1
    for d in date_range(START_DATE,END_DATE):
        if d.weekday()==0:
            for ch in CHANNELS:
                if ch[3]=="Brand":
                    rows.append((sid,d.isoformat(),ch[0],
                                 round(random.uniform(0.05,0.35),4),
                                 random.randint(5000,150000),
                                 round(random.uniform(0.2,0.9),3),
                                 random.randint(50,2000),
                                 random.randint(1000,50000),
                                 round(random.uniform(20,75),2),
                                 random.randint(50,500)))
                    sid+=1
    return rows

def build_attribution(conversions,touchpoints):
    rows=[]; aid=1
    tp_map={}
    for t in touchpoints:
        tp_map.setdefault(t[1],[]).append(t)
    for conv in conversions:
        cid=conv[1]; rev=float(conv[5])
        touches=sorted(tp_map.get(cid,[]),key=lambda x:x[4])
        if not touches: continue
        n=len(touches)
        weights=[math.exp(0.3*(j+1)) for j in range(n)]
        for i,t in enumerate(touches):
            seq=i+1
            ft=1.0 if seq==1 else 0.0
            lt=1.0 if seq==n else 0.0
            lin=round(1/n,6)
            td_w=round(weights[i]/sum(weights),6)
            if n==1: u=1.0
            elif n==2: u=0.5
            else:
                mid_w=0.20/(n-2) if n>2 else 0
                u=0.40 if seq==1 else (0.40 if seq==n else round(mid_w,6))
            rows.append((aid,conv[0],t[0],cid,t[2],t[3],t[4],seq,n,round(rev,2),
                         round(ft,6),round(lt,6),round(lin,6),round(td_w,6),round(u,6)))
            aid+=1
    return rows

def main():
    import os
    if os.path.exists(DB_PATH): os.remove(DB_PATH)
    print("Building realistic messy marketing attribution database...")
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    c.executescript(open("schema.sql").read())

    c.executemany("INSERT INTO dim_channel VALUES (?,?,?,?,?)",
                  [(ch[0],ch[1],ch[2],ch[3],ch[4]) for ch in CHANNELS])
    for p in PRODUCTS:
        c.execute("INSERT INTO dim_product VALUES (?,?,?,?,?,?)",p)

    date_rows=build_date_dim()
    c.executemany("INSERT INTO dim_date VALUES (?,?,?,?,?,?,?,?,?,?)",date_rows)

    campaigns=build_campaigns()
    c.executemany("INSERT INTO dim_campaign VALUES (?,?,?,?,?,?,?,?)",campaigns)

    customers=build_customers()
    c.executemany("INSERT INTO dim_customer VALUES (?,?,?,?,?,?,?,?,?)",customers)

    touchpoints=build_touchpoints(customers,campaigns)
    c.executemany("INSERT INTO fact_touchpoints VALUES (?,?,?,?,?,?,?,?,?,?,?)",touchpoints)

    conversions=build_conversions(customers,campaigns,touchpoints)
    c.executemany("INSERT INTO fact_conversions VALUES (?,?,?,?,?,?,?,?,?,?)",conversions)

    spend=build_spend(campaigns)
    c.executemany("INSERT INTO fact_spend VALUES (?,?,?,?,?,?,?,?,?,?)",spend)

    subscriptions=build_subscriptions(customers,conversions)
    c.executemany("INSERT INTO fact_subscriptions VALUES (?,?,?,?,?,?,?,?,?,?,?)",subscriptions)

    orders=build_orders(customers,conversions)
    c.executemany("INSERT INTO fact_orders VALUES (?,?,?,?,?,?,?)",orders)

    cart=build_cart_events(customers,campaigns)
    c.executemany("INSERT INTO fact_cart_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",cart)

    react=build_reactivation(customers,campaigns)
    c.executemany("INSERT INTO fact_reactivation_campaigns VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",react)

    brand=build_brand_signals(campaigns)
    c.executemany("INSERT INTO fact_brand_signals VALUES (?,?,?,?,?,?,?,?,?,?)",brand)

    attribution=build_attribution(conversions,touchpoints)
    c.executemany("INSERT INTO fact_attribution VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",attribution)

    conn.commit()
    total=sum([len(x) for x in [date_rows,campaigns,customers,touchpoints,conversions,
                                  spend,subscriptions,orders,cart,react,brand,attribution]])
    print(f"\n✓ Done. {total:,} rows across 14 tables.")
    print("\nProblems baked in:")
    print("  - Display + Paid Social: high spend, ROAS < 1.0")
    print("  - Email acquisition: churn rate 2x Organic")
    print("  - Organic: best LTV but lowest volume")
    print("  - '10% Off' cart offer: 12% recovery rate vs 42% for Free Month")
    print("  - Win-back (Churned) reactivation: 4% CVR — wasted spend")
    print("  - Occasional segment: LTV flatlines after 60 days")
    conn.close()

if __name__=="__main__":
    main()
