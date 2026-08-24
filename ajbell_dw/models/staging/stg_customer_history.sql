-- Staging model for customer_history - the versioned record of customer attributes over time.
-- This is our simulated change-data-capture (CDC) feed: most customers have one row,
-- but ~264 have multiple, each marking when their address/email changed.
-- This table is the raw material for the SCD Type 2 dim_customer we build next.

with source as (
    select * from {{ source('raw', 'customer_history') }}
)

select
    customer_history_id,   -- business key for this specific version row
    customer_id,           -- FK to the customer this version belongs to
    email,                 -- email as it was from valid_from onwards
    address_line,          -- address as it was from valid_from onwards
    city,
    postcode,
    valid_from             -- date this version became effective (start of its validity window)
from source