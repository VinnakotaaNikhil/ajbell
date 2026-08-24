-- Dimension: date (calendar).
-- Grain: one row per calendar day.
-- Not built from a source table - it's GENERATED with a date spine, then enriched
-- with useful calendar attributes so analysts can slice by year/quarter/month/etc.
-- without writing date logic in every query.

with date_spine as (
    -- dbt_utils.date_spine generates a continuous series of dates with no gaps.
    -- We cover a range wider than the trade data (2020-2027) to be safe.
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2020-01-01' as date)",
        end_date="cast('2028-01-01' as date)"
    ) }}
),

calendar as (
    select
        cast(date_day as date) as date_day   -- the actual calendar date (one row per day)
    from date_spine
)

select
    -- Surrogate key for the date, in clean YYYYMMDD integer form (e.g. 2024-03-15 -> 20240315).
    -- This is the standard date-dimension key; fact tables store this integer.
    cast(strftime(date_day, '%Y%m%d') as integer) as date_sk,

    date_day,                                          -- the date itself
    extract(year    from date_day) as year,
    extract(quarter from date_day) as quarter,
    extract(month   from date_day) as month,
    strftime(date_day, '%B')       as month_name,      -- e.g. "March"
    extract(day     from date_day) as day_of_month,
    extract(dow     from date_day) as day_of_week,     -- 0 = Sunday ... 6 = Saturday (DuckDB)
    strftime(date_day, '%A')       as day_name,        -- e.g. "Friday"
    case
        when extract(dow from date_day) in (0, 6) then true
        else false
    end as is_weekend                                  -- handy flag for weekday/weekend analysis
from calendar