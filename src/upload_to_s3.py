"""
Phase 3, Step 4 - Upload local Parquet extracts to Amazon S3.

Takes the Parquet files produced by extract_to_parquet.py and uploads each
to the S3 landing zone (the "raw" prefix). Uses boto3, the AWS SDK for Python,
which automatically picks up the credentials configured via `aws configure`
- so no keys ever appear in this code.
"""

import os
import boto3

# --- config -------------------------------------------------------------
BUCKET      = "ajbell-portfolio"       # your S3 bucket (created in the console)
EXTRACT_DIR = "data/extracts"         # local Parquet files from Step 3
RAW_PREFIX  = "raw"                   # top-level "folder" in the bucket for raw data

TABLES = [
    "customers",
    "customer_history",
    "accounts",
    "securities",
    "trades",
]

def main():
    # boto3 client for S3. Credentials come from ~/.aws/credentials (aws configure).
    s3 = boto3.client("s3")

    print(f"Uploading {len(TABLES)} files to s3://{BUCKET}/{RAW_PREFIX}/\n")

    for table in TABLES:
        local_path = f"{EXTRACT_DIR}/{table}.parquet"

        # The S3 "key" is the object's full name. Structuring it as
        # raw/<table>/<table>.parquet makes the console show tidy folders
        # and sets up per-table partitioning in the next step.
        s3_key = f"{RAW_PREFIX}/{table}/{table}.parquet"

        s3.upload_file(local_path, BUCKET, s3_key)
        size_kb = os.path.getsize(local_path) / 1024
        print(f"  {local_path:<40} -> s3://{BUCKET}/{s3_key}  ({size_kb:,.0f} KB)")

    print("\nUpload complete.")

if __name__ == "__main__":
    main()