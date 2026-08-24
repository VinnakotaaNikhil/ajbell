-- Dimension: customer, built as SCD Type 2 (one row per historical VERSION of a customer).
-- Source: stg_customer_history, which holds every version of a customer's mutable
-- attributes (email/address), each with the date it became effective (valid_from).
--
-- We add, per version:
--   valid_to    - when the version stopped being effective (= next version's valid_from)
--   is_current  - true for the version in force today
--   customer_sk - unique surrogate key per version (hash of customer_id + valid_from)
--
-- We also join the STATIC attributes (name, DOB, joined_date) from stg_customers,
-- since those don't change and don't live in the history table.

with history as (
    select * from {{ ref('stg_customer_history') }}
),

customers_static as (
    -- attributes that never change, so they aren't versioned in history
    select
        customer_id,
        first_name,
        last_name,
        date_of_birth,
        joined_date
    from {{ ref('stg_customers') }}
),

versioned as (
    select
        customer_id,
        email,
        address_line,
        city,
        postcode,
        valid_from,

        -- LEAD() looks at the NEXT version (ordered by valid_from) for the same customer.
        -- That next version's valid_from is exactly when THIS version stopped being valid.
        -- The newest version has no "next", so LEAD() returns NULL -> we handle that below.
        lead(valid_from) over (
            partition by customer_id      -- restart the sequence for each customer
            order by valid_from           -- oldest version first
        ) as next_valid_from

    from history
),

final as (
    select
        -- Surrogate key per VERSION: hashing customer_id + valid_from makes each
        -- version of the same customer a distinct, unique key. This is the core
        -- reason SCD2 needs surrogate keys.
        {{ dbt_utils.generate_surrogate_key(['v.customer_id', 'v.valid_from']) }} as customer_sk,

        v.customer_id as customer_bk,     -- business key (shared across a customer's versions)

        -- static attributes (same for every version of this customer)
        s.first_name,
        s.last_name,
        s.date_of_birth,
        s.joined_date,

        -- versioned attributes (differ between versions)
        v.email,
        v.address_line,
        v.city,
        v.postcode,

        -- validity window
        v.valid_from,
        -- if there's no next version, this is the current one -> use a far-future sentinel
        coalesce(v.next_valid_from, cast('9999-12-31' as date)) as valid_to,

        -- current-version flag: true only when there is no next version
        case when v.next_valid_from is null then true else false end as is_current

    from versioned v
    left join customers_static s
        on v.customer_id = s.customer_id
)

select * from final