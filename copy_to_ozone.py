#!/usr/bin/env python3
import argparse
import os
import sys

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


def parse_args():
    parser = argparse.ArgumentParser(
        description="Upload a local file or directory to an Apache Ozone bucket via the S3-compatible gateway."
    )
    parser.add_argument("source", metavar="source", help="Path to a local file or directory to upload")
    parser.add_argument("bucket", help="Target Ozone bucket name")
    parser.add_argument(
        "--key",
        help="Object key (file mode) or key prefix (directory mode); default: basename of source",
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
    return parser.parse_args()


def upload_one(s3, local_path, bucket, key):
    # Returns None on success, error string on failure
    try:
        s3.upload_file(local_path, bucket, key)
    except FileNotFoundError:
        return f"file not found: {local_path}"
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        message = e.response.get("Error", {}).get("Message", str(e))
        return f"S3 request failed ({code}): {message}"
    except BotoCoreError as e:
        return str(e)
    except OSError as e:
        return str(e)
    return None


def main():
    args = parse_args()

    source = args.source
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

    if os.path.isfile(source):
        key = args.key or os.path.basename(source)
        err = upload_one(s3, source, bucket, key)
        if err:
            print(f"Error: {err}", file=sys.stderr)
            sys.exit(1)
        print(f"Uploaded '{source}' -> s3://{bucket}/{key}  [{endpoint}]")

    elif os.path.isdir(source):
        # Collect only regular files directly inside the directory (non-recursive)
        files = [
            entry.name
            for entry in os.scandir(source)
            if entry.is_file()
        ]

        if not files:
            print(f"Warning: no regular files found in '{source}'", file=sys.stderr)
            sys.exit(0)

        # Normalise the prefix: strip trailing slash so joining is consistent
        prefix = args.key.rstrip("/") if args.key else None

        failed = 0
        for name in sorted(files):
            local_path = os.path.join(source, name)
            key = f"{prefix}/{name}" if prefix else name
            err = upload_one(s3, local_path, bucket, key)
            if err:
                print(f"Error: {err}", file=sys.stderr)
                failed += 1
            else:
                print(f"Uploaded '{local_path}' -> s3://{bucket}/{key}  [{endpoint}]")

        print(f"Batch complete: {len(files) - failed} file(s) uploaded.")
        if failed:
            print(f"{failed} file(s) failed.", file=sys.stderr)
            sys.exit(1)

    else:
        print(f"Error: source not found or not a file/directory: {source}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
