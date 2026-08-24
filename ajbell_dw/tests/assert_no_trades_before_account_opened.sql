-- Singular (custom) test: no trade should occur before its account was opened.
-- Convention for singular tests: SELECT the BAD rows. If any come back, the test FAILS.
-- Here "bad" = a trade whose timestamp predates its account's opened_date.

select
    f.trade_bk,
    f.trade_timestamp,
    a.opened_date
from {{ ref('fact_trades') }} f
join {{ ref('dim_account') }} a
    on f.account_sk = a.account_sk
where cast(f.trade_timestamp as date) < a.opened_date