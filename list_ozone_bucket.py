#!/usr/bin/env python3
import argparse
import os
import sys

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


def parse_args():
    parser = argparse.ArgumentParser(
        description="List the contents of an Apache Ozone bucket via the S3-compatible gateway."
    )
    parser.add_argument("bucket", help="Ozone bucket name to list")
    parser.add_argument(
        "--prefix",
        default="",
        help="Only list objects whose key starts with this prefix (default: list all)",
    )
    parser.add_argument(
        "--endpoint",
        default="http://localhost:9878",
        help="S3 Gateway URL (default: http://localhost:9878)",
    )
    parser.add_argument(
        "--access-key",
        default=os.environ.get("OZONE_ACCESS_KEY", "ozone"),
        help="S3 access key (default: OZONE_ACCESS_KEY env var or 'ozone')",
    )
    parser.add_argument(
        "--secret-key",
        default=os.environ.get("OZONE_SECRET_KEY", "ozone123"),
        help="S3 secret key (default: OZONE_SECRET_KEY env var or 'ozone123')",
    )
    parser.add_argument(
        "--long", "-l",
        action="store_true",
        help="Show full metadata: size, last modified, storage class, and key",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    bucket = args.bucket
    endpoint = args.endpoint.rstrip("/")

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=args.access_key,
        aws_secret_access_key=args.secret_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
        verify=False,
    )

    paginator = s3.get_paginator("list_objects_v2")
    page_kwargs = {"Bucket": bucket}
    if args.prefix:
        page_kwargs["Prefix"] = args.prefix

    objects = []
    try:
        for page in paginator.paginate(**page_kwargs):
            objects.extend(page.get("Contents", []))
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        message = e.response.get("Error", {}).get("Message", str(e))
        print(f"Error: S3 request failed ({code}): {message}", file=sys.stderr)
        sys.exit(1)
    except BotoCoreError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not objects:
        print(f"Bucket '{bucket}' is empty.", file=sys.stderr)
        sys.exit(0)

    if args.long:
        total_size = 0
        for obj in objects:
            size = obj["Size"]
            last_modified = obj["LastModified"].strftime("%Y-%m-%d %H:%M:%S")
            key = obj["Key"]
            total_size += size
            print(f"{size}\t{last_modified}\t{key}")
        print(f"\n{len(objects)} object(s), {total_size} byte(s) total")
    else:
        for obj in objects:
            print(obj["Key"])


if __name__ == "__main__":
    main()
