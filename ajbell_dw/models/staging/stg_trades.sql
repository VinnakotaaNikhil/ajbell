-- Staging model for trades - the transactional events (one row per buy/sell).
-- This is the grain that becomes fact_trades later.
-- Light work only here, PLUS one small typed helper: split the timestamp into a date
-- so downstream models can join to the date dimension easily.

with source as (
    select * from {{ source('raw', 'trades') }}
)

select
    trade_id,                              -- business key: uniquely identifies a trade
    account_id,                            -- FK to the account that placed the trade
    security_id,                           -- FK to the instrument traded
    trade_type,                            -- BUY / SELL
    quantity,                              -- number of units traded
    price,                                 -- price per unit at time of trade
    quantity * price as gross_amount,      -- derived: total value of the trade (units x price)
    trade_timestamp,                       -- full timestamp of the trade
    cast(trade_timestamp as date) as trade_date  -- date-only, used to join dim_date later
from source