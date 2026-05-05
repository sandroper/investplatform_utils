# investplatform-utils

Command-line utilities for interacting with the InvestPlatform infrastructure. All scripts target the Apache Ozone S3-compatible gateway.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Common options

All scripts share the same connection and credential flags:

| Flag | Default | Description |
|---|---|---|
| `--endpoint` | `http://localhost:9878` | Ozone S3 Gateway URL |
| `--access-key` | `OZONE_ACCESS_KEY` env or `ozone` | S3 access key |
| `--secret-key` | `OZONE_SECRET_KEY` env or `ozone123` | S3 secret key |

Credentials can also be set via environment variables to avoid repeating them on every call:

```bash
export OZONE_ACCESS_KEY=ozone
export OZONE_SECRET_KEY=ozone123
```

---

## copy_to_ozone.py

Upload a single file or all files in a directory to an Ozone bucket.

```
python copy_to_ozone.py <source> <bucket> [--key KEY] [options]
```

### Arguments

| Argument | Description |
|---|---|
| `source` | Path to a local file or directory |
| `bucket` | Target Ozone bucket name (e.g. `env01-inv-ml-data`) |
| `--key` | Object key (file mode) or key prefix (directory mode). Defaults to the source basename. |

### Single-file mode

When `source` is a file, uploads it to the bucket under the given key.

```bash
# Upload a file, key defaults to its filename
python copy_to_ozone.py photo.jpg env01-inv-ml-data

# Upload with an explicit key (including path prefix)
python copy_to_ozone.py photo.jpg env01-inv-ml-data --key 2026/04/28/photo.jpg
```

### Directory mode

When `source` is a directory, uploads every regular file directly inside it. Subdirectories are skipped. The `--key` value is used as a prefix for each object key.

```bash
# Upload all files in a directory; keys will be just the filenames
python copy_to_ozone.py ./images env01-inv-ml-data

# Upload all files under a key prefix (trailing slash optional)
python copy_to_ozone.py ./images env01-inv-ml-data --key 2026/04/28
# produces: 2026/04/28/photo1.jpg, 2026/04/28/photo2.jpg, ...
```

In directory mode, upload errors are non-fatal: all files are attempted, failures are reported to stderr, and the script exits with code 1 only if at least one file failed. A summary line is always printed at the end.

---

## list_ozone_bucket.py

List the contents of an Ozone bucket.

```
python list_ozone_bucket.py <bucket> [--prefix PREFIX] [--long] [options]
```

### Arguments

| Argument | Description |
|---|---|
| `bucket` | Ozone bucket name to list (e.g. `env01-inv-ml-data`) |
| `--prefix` | Only list objects whose key starts with this string |
| `--long`, `-l` | Show full metadata: size (bytes), last modified date, and key |

### Examples

```bash
# List all keys in a bucket (one per line, pipe-friendly)
python list_ozone_bucket.py env01-inv-ml-data

# Filter by prefix
python list_ozone_bucket.py env01-inv-ml-data --prefix 2026/04/

# Full metadata view
python list_ozone_bucket.py env01-inv-ml-data -l
# 149572   2026-04-28 13:13:32   2026/04/28/photo.jpg
# ...
# 3 object(s), 450000 byte(s) total

# Combine prefix filter with long output
python list_ozone_bucket.py env01-inv-ml-data --prefix 2026/04/28/ -l
```

The script uses pagination internally, so it handles buckets with more than 1000 objects correctly. If the bucket is empty (or no objects match the prefix), a message is printed to stderr and the script exits with code 0.
