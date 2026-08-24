-- Staging model for accounts.
-- One row per account. Each account belongs to a customer and has a type (ISA/Pension/Dealing).
-- Light work only: select, rename, cast. No joins, no business logic.

with source as (
    select * from {{ source('raw', 'accounts') }}
)

select
    account_id,        -- business key: uniquely identifies an account
    customer_id,       -- foreign key back to the owning customer
    account_type,      -- ISA / Pension / Dealing
    account_status,    -- Active / Closed
    opened_date        -- date the account was opened (always >= customer's joined_date)
from source