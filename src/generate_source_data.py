"""
Phase 1 - Source system data generator (AJ Bell ELT portfolio project)

Generates a realistic, internally-consistent investment-platform dataset
and writes it to a DuckDB file that acts as our source (OLTP) system.

Tables produced:
  customers          - one row per customer (current state)
  accounts           - each customer holds 1-3 accounts (ISA / Pension / Dealing)
  securities         - the investable instruments
  trades             - buy/sell events (this becomes the fact table in Phase 2)
  customer_history   - versioned customer attributes over time; this is what
                       lets us build a real SCD Type 2 dimension in Phase 2.
                       Think of it as a change-data-capture (CDC) feed - the
                       same thing tools like Fivetran HVR produce.

Re-running this script fully rebuilds the database (it's idempotent).
"""

import os
import random
from datetime import date, datetime, timedelta

import duckdb
from faker import Faker

# --------------------------------------------------------------------------
# CONFIG  - change these to regenerate at a different size
# --------------------------------------------------------------------------
N_CUSTOMERS   = 1000
TARGET_TRADES = 50_000
HISTORY_YEARS = 5
SEED          = 42
DB_PATH       = "data/source.duckdb"

END_DATE   = date.today()
START_DATE = END_DATE - timedelta(days=365 * HISTORY_YEARS)

random.seed(SEED)
fake = Faker("en_GB")
Faker.seed(SEED)

# --------------------------------------------------------------------------
# Reference data: securities (ticker, name, asset_class, sector, currency, base_price)
# --------------------------------------------------------------------------
SECURITIES = [
    ("VOD.L",  "Vodafone Group",            "Equity", "Telecoms",       "GBP",   0.75),
    ("BP.L",   "BP",                        "Equity", "Energy",         "GBP",   4.80),
    ("HSBA.L", "HSBC Holdings",             "Equity", "Financials",     "GBP",   6.50),
    ("GSK.L",  "GSK",                       "Equity", "Healthcare",     "GBP",  15.20),
    ("AZN.L",  "AstraZeneca",               "Equity", "Healthcare",     "GBP", 105.00),
    ("ULVR.L", "Unilever",                  "Equity", "Consumer",       "GBP",  42.00),
    ("SHEL.L", "Shell",                     "Equity", "Energy",         "GBP",  25.50),
    ("RIO.L",  "Rio Tinto",                 "Equity", "Materials",      "GBP",  52.00),
    ("BARC.L", "Barclays",                  "Equity", "Financials",     "GBP",   1.85),
    ("LLOY.L", "Lloyds Banking Group",      "Equity", "Financials",     "GBP",   0.52),
    ("TSCO.L", "Tesco",                     "Equity", "Consumer",       "GBP",   2.95),
    ("NG.L",   "National Grid",             "Equity", "Utilities",      "GBP",  10.40),
    ("AAPL",   "Apple",                     "Equity", "Technology",     "USD", 190.00),
    ("MSFT",   "Microsoft",                 "Equity", "Technology",     "USD", 420.00),
    ("AMZN",   "Amazon",                    "Equity", "Consumer",       "USD", 178.00),
    ("GOOGL",  "Alphabet",                  "Equity", "Technology",     "USD", 165.00),
    ("NVDA",   "NVIDIA",                    "Equity", "Technology",     "USD", 120.00),
    ("TSLA",   "Tesla",                     "Equity", "Consumer",       "USD", 250.00),
    ("JPM",    "JPMorgan Chase",            "Equity", "Financials",     "USD", 205.00),
    ("KO",     "Coca-Cola",                 "Equity", "Consumer",       "USD",  62.00),
    ("VUSA.L", "Vanguard S&P 500 ETF",      "ETF",    "Broad Market",   "GBP",  85.00),
    ("VWRL.L", "Vanguard FTSE All-World",   "ETF",    "Broad Market",   "GBP", 110.00),
    ("ISF.L",  "iShares Core FTSE 100",     "ETF",    "UK Equity",      "GBP",   8.20),
    ("EQQQ.L", "Invesco Nasdaq-100 ETF",    "ETF",    "Technology",     "GBP", 380.00),
    ("VMID.L", "Vanguard FTSE 250 ETF",     "ETF",    "UK Equity",      "GBP",  32.00),
    ("SGLN.L", "iShares Physical Gold",     "ETF",    "Commodities",    "GBP",  45.00),
    ("VFEM.L", "Vanguard Emerging Markets", "ETF",    "Emerging",       "GBP",  52.00),
    ("FCIT.L", "F&C Investment Trust",      "Fund",   "Global",         "GBP",  10.80),
    ("SMT.L",  "Scottish Mortgage IT",      "Fund",   "Global Growth",  "GBP",   8.90),
    ("CTY.L",  "City of London IT",         "Fund",   "UK Income",      "GBP",   4.20),
    ("LGGL",   "L&G Global Equity Fund",    "Fund",   "Global",         "GBP",   1.65),
    ("FGGL",   "Fidelity Global Fund",      "Fund",   "Global",         "GBP",   2.30),
    ("UKGB29", "UK Gilt 2029",              "Bond",   "Government",     "GBP",  96.50),
    ("UKGB34", "UK Gilt 2034",              "Bond",   "Government",     "GBP",  92.00),
    ("UKGB40", "UK Gilt 2040",              "Bond",   "Government",     "GBP",  88.50),
    ("CORP27", "Corporate Bond 2027",       "Bond",   "Corporate",     "GBP",  99.20),
    ("CORP31", "Corporate Bond 2031",       "Bond",   "Corporate",     "GBP",  97.80),
    ("USTB30", "US Treasury 2030",          "Bond",   "Government",     "USD",  95.00),
]

ACCOUNT_TYPES = ["ISA", "Pension", "Dealing"]


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def random_datetime(start: date, end: date) -> datetime:
    start_dt = datetime.combine(start, datetime.min.time())
    span = int((datetime.combine(end, datetime.min.time()) - start_dt).total_seconds())
    return start_dt + timedelta(seconds=random.randint(0, max(span, 1)))


# --------------------------------------------------------------------------
# Generate customers + their history (versioned attributes for SCD2)
# --------------------------------------------------------------------------
customers = []          # current-state rows
customer_history = []   # every version, ordered by valid_from
hist_id = 0

for cid in range(1, N_CUSTOMERS + 1):
    first = fake.first_name()
    last = fake.last_name()
    dob = fake.date_of_birth(minimum_age=18, maximum_age=85)
    joined = random_date(START_DATE, END_DATE)

    # initial version at join date
    email = f"{first.lower()}.{last.lower()}{random.randint(1, 999)}@example.com"
    address = fake.street_address()
    city = fake.city()
    postcode = fake.postcode()
    valid_from = joined

    versions = [(email, address, city, postcode, valid_from)]

    # ~30% of customers move / change details 1-3 times after joining
    if random.random() < 0.30:
        for _ in range(random.randint(1, 3)):
            # only add a change if there's a reasonable window left
            if (END_DATE - valid_from).days < 180:
                break
            valid_from = random_date(valid_from + timedelta(days=90), END_DATE)
            address = fake.street_address()
            city = fake.city()
            postcode = fake.postcode()
            if random.random() < 0.5:  # sometimes email changes too
                email = f"{first.lower()}.{last.lower()}{random.randint(1, 999)}@example.com"
            versions.append((email, address, city, postcode, valid_from))

    for (e, a, c, p, vf) in versions:
        hist_id += 1
        customer_history.append((hist_id, cid, e, a, c, p, vf))

    # current state = latest version
    e, a, c, p, _ = versions[-1]
    customers.append((cid, first, last, dob, e, a, c, p, "United Kingdom", joined))

# --------------------------------------------------------------------------
# Generate accounts (1-3 per customer)
# --------------------------------------------------------------------------
accounts = []
account_id = 0
account_open = {}  # account_id -> opened_date, for trade date bounds

for (cid, _f, _l, _dob, _e, _a, _c, _p, _country, joined) in customers:
    for _ in range(random.choices([1, 2, 3], weights=[45, 40, 15])[0]):
        account_id += 1
        acc_type = random.choice(ACCOUNT_TYPES)
        opened = random_date(joined, END_DATE)
        status = "Active" if random.random() < 0.90 else "Closed"
        accounts.append((account_id, cid, acc_type, status, opened))
        account_open[account_id] = opened

# --------------------------------------------------------------------------
# Generate securities rows (with surrogate id)
# --------------------------------------------------------------------------
securities = []
sec_base_price = {}
for sid, (ticker, name, aclass, sector, ccy, base) in enumerate(SECURITIES, start=1):
    securities.append((sid, ticker, name, aclass, sector, ccy))
    sec_base_price[sid] = base

# --------------------------------------------------------------------------
# Generate trades (~TARGET_TRADES), weighted so older accounts trade more
# --------------------------------------------------------------------------
account_ids = [a[0] for a in accounts]
weights = [(END_DATE - account_open[aid]).days + 1 for aid in account_ids]
chosen = random.choices(account_ids, weights=weights, k=TARGET_TRADES)

trades = []
for trade_id, aid in enumerate(chosen, start=1):
    sid = random.randint(1, len(SECURITIES))
    trade_type = random.choices(["BUY", "SELL"], weights=[55, 45])[0]
    quantity = random.randint(1, 500)
    price = round(sec_base_price[sid] * random.uniform(0.7, 1.3), 2)
    ts = random_datetime(account_open[aid], END_DATE)
    trades.append((trade_id, aid, sid, trade_type, quantity, price, ts))

# --------------------------------------------------------------------------
# Write everything to DuckDB
# --------------------------------------------------------------------------
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
con = duckdb.connect(DB_PATH)

con.execute("""
CREATE OR REPLACE TABLE customers (
    customer_id   INTEGER,
    first_name    VARCHAR,
    last_name     VARCHAR,
    date_of_birth DATE,
    email         VARCHAR,
    address_line  VARCHAR,
    city          VARCHAR,
    postcode      VARCHAR,
    country       VARCHAR,
    joined_date   DATE
);""")
con.execute("""
CREATE OR REPLACE TABLE customer_history (
    customer_history_id INTEGER,
    customer_id         INTEGER,
    email               VARCHAR,
    address_line        VARCHAR,
    city                VARCHAR,
    postcode            VARCHAR,
    valid_from          DATE
);""")
con.execute("""
CREATE OR REPLACE TABLE accounts (
    account_id     INTEGER,
    customer_id    INTEGER,
    account_type   VARCHAR,
    account_status VARCHAR,
    opened_date    DATE
);""")
con.execute("""
CREATE OR REPLACE TABLE securities (
    security_id   INTEGER,
    ticker        VARCHAR,
    security_name VARCHAR,
    asset_class   VARCHAR,
    sector        VARCHAR,
    currency      VARCHAR
);""")
con.execute("""
CREATE OR REPLACE TABLE trades (
    trade_id        INTEGER,
    account_id      INTEGER,
    security_id     INTEGER,
    trade_type      VARCHAR,
    quantity        INTEGER,
    price           DOUBLE,
    trade_timestamp TIMESTAMP
);""")

con.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?,?)", customers)
con.executemany("INSERT INTO customer_history VALUES (?,?,?,?,?,?,?)", customer_history)
con.executemany("INSERT INTO accounts VALUES (?,?,?,?,?)", accounts)
con.executemany("INSERT INTO securities VALUES (?,?,?,?,?,?)", securities)
con.executemany("INSERT INTO trades VALUES (?,?,?,?,?,?,?)", trades)

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
print(f"Database written to: {DB_PATH}")
print(f"  customers        : {len(customers):>7,}")
print(f"  customer_history : {len(customer_history):>7,}  (rows beyond {len(customers)} = tracked changes)")
print(f"  accounts         : {len(accounts):>7,}")
print(f"  securities       : {len(securities):>7,}")
print(f"  trades           : {len(trades):>7,}")
print(f"  trade date range : {START_DATE} to {END_DATE}")

sample = con.execute("""
    SELECT t.trade_type, s.ticker, t.quantity, t.price, t.trade_timestamp
    FROM trades t JOIN securities s ON t.security_id = s.security_id
    ORDER BY t.trade_timestamp DESC LIMIT 5
""").fetchall()
print("\nMost recent 5 trades:")
for r in sample:
    print("  ", r)

con.close()