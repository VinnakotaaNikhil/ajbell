-- Staging model for securities (the investable instruments: equities, ETFs, funds, bonds).
-- Light work only: select, rename, cast. No joins, no business logic.

with source as (
    select * from {{ source('raw', 'securities') }}
)

select
    security_id,       -- business key: uniquely identifies an instrument
    ticker,            -- market ticker symbol, e.g. VOD.L, AAPL
    security_name,     -- human-readable name, e.g. "Vodafone Group"
    asset_class,       -- Equity / ETF / Fund / Bond
    sector,            -- broad classification, e.g. Financials, Technology
    currency           -- GBP / USD
from source