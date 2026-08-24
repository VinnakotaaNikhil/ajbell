-- Staging model for customers.
-- Purpose: one clean, typed, renamed view of the raw customers table.
-- Rule for staging: light work only (select, rename, cast) - no joins, no business logic.

with source as (
    -- pull everything from the raw source table declared in _sources.yml
    select * from {{ source('raw', 'customers') }}
)

select
    customer_id,        -- business key: uniquely identifies a customer in the source
    first_name,
    last_name,
    date_of_birth,
    email,              -- current email (latest value; history lives in customer_history)
    address_line,       -- current address (latest value)
    city,
    postcode,
    country,
    joined_date         -- date the customer joined the platform
from source