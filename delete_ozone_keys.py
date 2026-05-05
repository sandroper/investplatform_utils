#!/usr/bin/env python3
import argparse
import os
import sys

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

_BATCH_SIZE = 1000


def parse_args():
    parser = argparse.ArgumentParser(
        description="Delete objects from an Apache Ozone bucket via the S3-compatible gateway."
    )
    parser.add_argument("bucket", help="Ozone bucket name")
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

    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--key", metavar="KEY", help="Delete a single object by key.")
    action.add_argument("--all", action="store_true", help="Delete every object in the bucket.")

    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip the confirmation prompt when using --all.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be deleted without calling any delete API.",
    )
    return parser.parse_args()


def build_client(endpoint, access_key, secret_key):
    return boto3.client(
        "s3",
        endpoint_url=endpoint.rstrip("/"),
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
        verify=False,
    )


def delete_single(s3, bucket, key, dry_run):
    if dry_run:
        print(f"[dry-run] Would delete: s3://{bucket}/{key}")
        return

    try:
        s3.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            print(f"Error: key '{key}' does not exist in bucket '{bucket}'.", file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        s3.delete_object(Bucket=bucket, Key=key)
    except (ClientError, BotoCoreError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Deleted: s3://{bucket}/{key}")


def list_all_keys(s3, bucket):
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=bucket):
            keys.extend(obj["Key"] for obj in page.get("Contents", []))
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        message = e.response.get("Error", {}).get("Message", str(e))
        print(f"Error: S3 request failed ({code}): {message}", file=sys.stderr)
        sys.exit(1)
    except BotoCoreError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    return keys


def delete_all(s3, bucket, dry_run, yes):
    keys = list_all_keys(s3, bucket)

    if not keys:
        print(f"Bucket '{bucket}' is already empty.")
        return

    if dry_run:
        for key in keys:
            print(f"[dry-run] Would delete: s3://{bucket}/{key}")
        print(f"[dry-run] {len(keys)} object(s) would be deleted from bucket '{bucket}'.")
        return

    if not yes:
        answer = input(f"Delete all {len(keys)} object(s) in bucket '{bucket}'? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    deleted = 0
    for i in range(0, len(keys), _BATCH_SIZE):
        batch = [{"Key": k} for k in keys[i : i + _BATCH_SIZE]]
        try:
            response = s3.delete_objects(
                Bucket=bucket,
                Delete={"Objects": batch, "Quiet": True},
            )
        except (ClientError, BotoCoreError) as e:
            print(f"Error during bulk delete: {e}", file=sys.stderr)
            sys.exit(1)

        errors = response.get("Errors", [])
        if errors:
            for err in errors:
                print(
                    f"Error deleting '{err.get('Key')}': [{err.get('Code')}] {err.get('Message')}",
                    file=sys.stderr,
                )
            sys.exit(1)

        deleted += len(batch)

    print(f"Deleted {deleted} object(s) from bucket '{bucket}'.")


def main():
    args = parse_args()
    s3 = build_client(args.endpoint, args.access_key, args.secret_key)

    if args.key:
        delete_single(s3, args.bucket, args.key, args.dry_run)
    else:
        delete_all(s3, args.bucket, args.dry_run, args.yes)


if __name__ == "__main__":
    main()
