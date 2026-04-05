-- ============================================================
-- B2C SUBSCRIPTION BRAND — MARKETING ATTRIBUTION PLATFORM
-- Full lifecycle: Acquire → Convert → Retain → Reactivate
-- ============================================================

-- DIMENSIONS
CREATE TABLE dim_customer (
    customer_id         INTEGER PRIMARY KEY,
    first_seen_date     DATE,
    acquisition_channel VARCHAR(50),
    acquisition_campaign VARCHAR(100),
    segment             VARCHAR(30),   -- 'High Value','Mid Tier','Occasional','At Risk','Churned'
    region              VARCHAR(30),
    device_type         VARCHAR(20),   -- 'Mobile','Desktop','Tablet'
    age_group           VARCHAR(20),   -- '18-24','25-34','35-44','45-54','55+'
    lifecycle_stage     VARCHAR(30)    -- 'Prospect','Trial','Active','At Risk','Churned','Reactivated'
);

CREATE TABLE dim_channel (
    channel_id      INTEGER PRIMARY KEY,
    channel_name    VARCHAR(50),
    channel_type    VARCHAR(20),
    channel_group   VARCHAR(30),
    source_platform VARCHAR(50)
);

CREATE TABLE dim_campaign (
    campaign_id     INTEGER PRIMARY KEY,
    channel_id      INTEGER,
    campaign_name   VARCHAR(100),
    objective       VARCHAR(30),   -- 'Awareness','Consideration','Conversion','Retention','Reactivation'
    start_date      DATE,
    end_date        DATE,
    target_segment  VARCHAR(30),
    offer_type      VARCHAR(30)    -- 'None','Discount','Free Trial','Incentive','Win-back'
);

CREATE TABLE dim_date (
    date_id         INTEGER PRIMARY KEY,
    full_date       DATE,
    year            INTEGER,
    quarter         INTEGER,
    month           INTEGER,
    month_name      VARCHAR(20),
    week            INTEGER,
    day_of_week     INTEGER,
    day_name        VARCHAR(20),
    is_weekend      BOOLEAN
);

CREATE TABLE dim_product (
    product_id      INTEGER PRIMARY KEY,
    product_name    VARCHAR(100),
    category        VARCHAR(50),
    plan_type       VARCHAR(30),   -- 'Monthly','Annual','Trial'
    price_monthly   DECIMAL(8,2),
    price_annual    DECIMAL(8,2)
);

-- FACTS
CREATE TABLE fact_touchpoints (
    touchpoint_id   INTEGER PRIMARY KEY,
    customer_id     INTEGER,
    channel_id      INTEGER,
    campaign_id     INTEGER,
    touch_date      DATE,
    touch_timestamp DATETIME,
    touch_type      VARCHAR(30),   -- 'Impression','Click','Email Open','Email Click','Organic Visit','Direct Visit'
    session_id      VARCHAR(50),
    device_type     VARCHAR(20),
    is_paid         BOOLEAN,
    touch_sequence  INTEGER        -- position in customer journey (1=first, N=last)
);

CREATE TABLE fact_conversions (
    conversion_id       INTEGER PRIMARY KEY,
    customer_id         INTEGER,
    campaign_id         INTEGER,
    conversion_date     DATE,
    conversion_type     VARCHAR(30),   -- 'Trial Start','Subscription Start','Upsell','Reactivation'
    revenue             DECIMAL(10,2),
    product_id          INTEGER,
    is_first_conversion BOOLEAN,
    days_to_convert     INTEGER,       -- days from first touch to conversion
    touches_to_convert  INTEGER        -- number of touchpoints before conversion
);

CREATE TABLE fact_spend (
    spend_id        INTEGER PRIMARY KEY,
    channel_id      INTEGER,
    campaign_id     INTEGER,
    spend_date      DATE,
    daily_spend     DECIMAL(10,2),
    impressions     INTEGER,
    clicks          INTEGER,
    ctr             DECIMAL(6,4),
    cpc             DECIMAL(8,2),
    cpm             DECIMAL(8,2)
);

CREATE TABLE fact_subscriptions (
    subscription_id     INTEGER PRIMARY KEY,
    customer_id         INTEGER,
    product_id          INTEGER,
    start_date          DATE,
    end_date            DATE,
    status              VARCHAR(20),   -- 'Active','Cancelled','Paused','Upgraded','Downgraded'
    plan_type           VARCHAR(20),   -- 'Monthly','Annual','Trial'
    mrr                 DECIMAL(10,2),
    event_type          VARCHAR(30),   -- 'New','Renewal','Upgrade','Downgrade','Pause','Cancel'
    event_date          DATE,
    cancellation_reason VARCHAR(100)
);

CREATE TABLE fact_orders (
    order_id        INTEGER PRIMARY KEY,
    customer_id     INTEGER,
    product_id      INTEGER,
    order_date      DATE,
    revenue         DECIMAL(10,2),
    is_renewal      BOOLEAN,
    order_number    INTEGER          -- 1=first, 2=second, etc.
);

CREATE TABLE fact_cart_events (
    cart_event_id   INTEGER PRIMARY KEY,
    customer_id     INTEGER,
    product_id      INTEGER,
    campaign_id     INTEGER,
    event_date      DATE,
    event_timestamp DATETIME,
    event_type      VARCHAR(20),   -- 'Add','Abandon','Recover','Expire'
    cart_value      DECIMAL(10,2),
    recovery_channel VARCHAR(50),  -- channel used in follow-up if recovered
    recovery_days   INTEGER,       -- days between abandon and recovery
    offer_applied   VARCHAR(50)    -- discount or incentive used to recover
);

CREATE TABLE fact_reactivation_campaigns (
    reactivation_id     INTEGER PRIMARY KEY,
    customer_id         INTEGER,
    campaign_id         INTEGER,
    channel_id          INTEGER,
    trigger_date        DATE,
    trigger_reason      VARCHAR(50),   -- 'Churned','At Risk','Low Activity','Abandoned Cart'
    days_inactive       INTEGER,
    offer_type          VARCHAR(50),   -- 'Discount','Free Month','Feature Unlock','None'
    offer_value         DECIMAL(8,2),
    message_sent_date   DATE,
    converted           BOOLEAN,
    conversion_date     DATE,
    conversion_revenue  DECIMAL(10,2)
);

CREATE TABLE fact_brand_signals (
    signal_id       INTEGER PRIMARY KEY,
    signal_date     DATE,
    channel_id      INTEGER,
    share_of_voice  DECIMAL(6,4),   -- % of total category mentions
    organic_reach   INTEGER,
    sentiment_score DECIMAL(4,3),   -- -1.0 to 1.0
    mentions        INTEGER,
    branded_searches INTEGER,
    nps_score       DECIMAL(5,2),
    nps_responses   INTEGER
);

CREATE TABLE fact_attribution (
    attribution_id      INTEGER PRIMARY KEY,
    conversion_id       INTEGER,
    touchpoint_id       INTEGER,
    customer_id         INTEGER,
    channel_id          INTEGER,
    campaign_id         INTEGER,
    touch_date          DATE,
    touch_sequence      INTEGER,
    total_touches       INTEGER,
    conversion_revenue  DECIMAL(10,2),
    -- attribution credit by model
    credit_first_touch  DECIMAL(6,4),
    credit_last_touch   DECIMAL(6,4),
    credit_linear       DECIMAL(6,4),
    credit_time_decay   DECIMAL(6,4),
    credit_u_shaped     DECIMAL(6,4)
);
