{{config(materialized='incremental',
         unique_key='trade_bk',
         incremental_strategy='merge')}}
with trades as (
    select * from {{ ref('stg_trades') }}
),

accounts as (
    -- we need account_sk (surrogate) keyed by account_bk (business) to join on
    select account_bk, account_sk from {{ ref('dim_account') }}
),

securities as (
    select security_bk, security_sk from {{ ref('dim_security') }}
),

final as(
    select
        -- Degenerate dimension: the trade's own business key, kept on the fact for traceability.
        t.trade_id as trade_bk,

        -- Foreign keys OUT to the dimensions (surrogate keys) -------------------
        a.account_sk,                                   -- links to dim_account (and via it, the customer)
        s.security_sk,                                  -- links to dim_security
        cast(strftime(t.trade_date, '%Y%m%d') as integer) as date_sk,  -- links to dim_date (YYYYMMDD)

        -- Measures (the numbers you aggregate) ---------------------------------
        t.trade_type,                                   -- BUY / SELL (kept here as it describes the event)
        t.quantity,
        t.price,
        t.gross_amount,                                 -- quantity * price, computed back in staging

        -- Timestamp kept for fine-grained analysis if needed
        t.trade_timestamp

    from trades t
    left join accounts   a on t.account_id  = a.account_bk    -- swap account business key -> surrogate key
    left join securities s on t.security_id = s.security_bk   -- swap security business key -> surrogate key
)

select * from final

{% if is_incremental() %}

    where trade_timestamp > (select max(trade_timestamp) from {{ this }})
{% endif %}