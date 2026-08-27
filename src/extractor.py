"""
Phase 3, Step 3 - Extract source tables from DuckDB to local Parquet files.

Reads each table from the DuckDB source database and writes it out as a
Parquet file under data/extracts/. This is the "E" of ELT done locally;
Step 4 adds the upload to S3.

Parquet is chosen over CSV because it is columnar, compresses well, and
stores the schema (data types) with the data - the standard landing format
for analytics warehouses like Snowflake.
"""

import os
import duckdb

# --- config -------------------------------------------------------------
SOURCE_DB   = "data/source.duckdb"          # the source system (from Phase 1)
EXTRACT_DIR = "data/extracts"               # where Parquet files land locally

# the five tables we want to pull out of the source
TABLES = [
    "customers",
    "customer_history",
    "accounts",
    "securities",
    "trades",
]

def main():
    # make sure the output folder exists
    os.makedirs(EXTRACT_DIR, exist_ok=True)

    # open a read-only connection to the source database.
    # read_only=True is deliberate: an extractor should never modify its source,
    # and it also avoids the write-lock problems we hit earlier.
    con = duckdb.connect(SOURCE_DB, read_only=True)

    print(f"Extracting {len(TABLES)} tables from {SOURCE_DB}\n")

    for table in TABLES:
        out_path = f"{EXTRACT_DIR}/{table}.parquet"

        # DuckDB can write a query result straight to Parquet with COPY.
        # We select everything from the table and write it to the file.
        con.execute(f"""
            COPY (SELECT * FROM {table})
            TO '{out_path}'
            (FORMAT PARQUET)
        """)

        # read back the row count so we can confirm the extract worked
        rows = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        size_kb = os.path.getsize(out_path) / 1024
        print(f"  {table:<18} -> {out_path:<35} {rows:>7,} rows  ({size_kb:,.0f} KB)")

    con.close()
    print("\nExtraction complete.")

if __name__ == "__main__":
    main()