-- Dimension: accounts.
-- Grain: one row per account. Type 1 dimension (current state, no history).

with accounts as (
    select * from {{ ref('stg_accounts') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['account_id']) }} as account_sk,  -- warehouse surrogate key

    account_id  as account_bk,   -- business key from source
    customer_id as customer_bk,  -- business key of owning customer (used to link to dim_customer later)
    account_type,                -- ISA / Pension / Dealing
    account_status,              -- Active / Closed
    opened_date
from accounts