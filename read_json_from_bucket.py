#!/usr/bin/env python3
import argparse
import json
import os
import sys

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


def parse_args():
    parser = argparse.ArgumentParser(
        description="Read a JSON file from an Apache Ozone bucket via the S3-compatible gateway and pretty-print it."
    )
    parser.add_argument("bucket", help="Ozone bucket name")
    parser.add_argument("key", help="S3 object key of the JSON file")
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

    try:
        response = s3.get_object(Bucket=bucket, Key=args.key)
        body = response["Body"].read().decode("utf-8")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        message = e.response.get("Error", {}).get("Message", str(e))
        print(f"Error: S3 request failed ({code}): {message}", file=sys.stderr)
        sys.exit(1)
    except BotoCoreError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        print(f"Error: object is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
