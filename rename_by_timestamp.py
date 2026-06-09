#!/usr/bin/env python3
"""
rename_by_timestamp.py

Renames files whose names contain an epoch timestamp (with or without milliseconds)
to a human-readable datetime format: dd-mm-yyyy_hh-mm-ss[_suffix].ext

Usage:
    python rename_by_timestamp.py <folder_path> [--timezone UTC] [--dry-run] [--log rename_log.txt]

Arguments:
    folder_path         Path to the folder containing files to rename
    --timezone          Timezone name (default: local system time). E.g. "UTC", "Europe/Oslo"
    --dry-run           Preview changes without renaming any files
    --log               Path to the log file (default: rename_log.txt in the target folder)

Examples:
    python rename_by_timestamp.py /path/to/files
    python rename_by_timestamp.py /path/to/files --timezone UTC --dry-run
    python rename_by_timestamp.py C:\\files\\Videos --log C:\\Logs\\rename.txt
"""

import os
import re
import sys
import argparse
import datetime


# ---------------------------------------------------------------------------
# Timestamp detection
# ---------------------------------------------------------------------------

# Patterns ordered from most-specific (longest) to least-specific.
# Each pattern captures the numeric timestamp in group 1.
TIMESTAMP_PATTERNS = [
    # 13-digit millisecond epoch (e.g. 1779040856055)
    re.compile(r'(?<!\d)(\d{13})(?!\d)'),
    # 10-digit second epoch (e.g. 1779040856)
    re.compile(r'(?<!\d)(\d{10})(?!\d)'),
]

# Sanity bounds: timestamps must fall within this range
# (2000-01-01 00:00:00 UTC  …  2100-01-01 00:00:00 UTC)
TS_MIN_S = 946_684_800
TS_MAX_S = 4_102_444_800


def extract_timestamp(filename: str):
    """
    Try to find a valid epoch timestamp inside *filename* (stem only).
    Returns (timestamp_seconds: float, match_object) or (None, None).
    """
    stem = os.path.splitext(filename)[0]

    for pattern in TIMESTAMP_PATTERNS:
        for match in pattern.finditer(stem):
            raw = int(match.group(1))
            # Convert milliseconds → seconds if needed
            ts_s = raw / 1000 if len(match.group(1)) == 13 else float(raw)
            if TS_MIN_S <= ts_s <= TS_MAX_S:
                return ts_s, match

    return None, None


# ---------------------------------------------------------------------------
# Naming helpers
# ---------------------------------------------------------------------------

def ts_to_datetime(ts_s: float, tz: datetime.timezone) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(ts_s, tz=tz)


def build_new_stem(dt: datetime.datetime, existing_stems: set, original_stem: str) -> str:
    """
    Produce  dd-mm-yyyy_hh-mm-ss  and append a counter suffix if that name
    already exists (collision avoidance).
    """
    base = dt.strftime('%d-%m-%Y_%H-%M-%S')
    candidate = base
    counter = 1
    while candidate in existing_stems:
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def process_folder(folder: str, tz: datetime.timezone, dry_run: bool, log_path: str):
    if not os.path.isdir(folder):
        print(f"ERROR: '{folder}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    entries = sorted(os.listdir(folder))
    files = [e for e in entries if os.path.isfile(os.path.join(folder, e))]

    log_lines = []
    log_lines.append(f"Rename log — {'DRY RUN — ' if dry_run else ''}generated {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    log_lines.append(f"Folder   : {os.path.abspath(folder)}")
    log_lines.append(f"Timezone : {tz}")
    log_lines.append("=" * 70)

    # Track stems that will exist after renaming to avoid collisions
    used_stems: set = set()
    # Pre-populate with stems of files that will NOT be renamed
    for fname in files:
        ts_s, _ = extract_timestamp(fname)
        if ts_s is None:
            used_stems.add(os.path.splitext(fname)[0])

    renamed = skipped = errors = 0

    for fname in files:
        ts_s, match = extract_timestamp(fname)
        ext = os.path.splitext(fname)[1]

        if ts_s is None:
            log_lines.append(f"\nOriginal filename : {fname}")
            log_lines.append(f"  SKIPPED — no valid epoch timestamp found in filename")
            skipped += 1
            continue

        dt = ts_to_datetime(ts_s, tz)
        new_stem = build_new_stem(dt, used_stems, os.path.splitext(fname)[0])
        new_fname = new_stem + ext

        src = os.path.join(folder, fname)
        dst = os.path.join(folder, new_fname)

        log_lines.append(f"\nOriginal filename : {fname}")
        log_lines.append(f"Calculated date   : {dt:%d.%m.%Y %H:%M:%S}")
        log_lines.append(f"New filename      : {new_fname}")

        if dry_run:
            log_lines.append(f"  [DRY RUN — not renamed]")
        else:
            try:
                os.rename(src, dst)
                used_stems.add(new_stem)
                log_lines.append(f"  Status            : OK")
                renamed += 1
            except OSError as e:
                log_lines.append(f"  Status            : ERROR — {e}")
                errors += 1
                continue

        used_stems.add(new_stem)

    log_lines.append("\n" + "=" * 70)
    log_lines.append(f"Summary: {renamed} renamed, {skipped} skipped, {errors} errors")
    if dry_run:
        log_lines.append("(Dry run — no files were actually renamed)")

    log_text = "\n".join(log_lines)

    # Write log
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(log_text + "\n")
        print(f"Log written to: {log_path}")
    except OSError as e:
        print(f"WARNING: Could not write log file: {e}", file=sys.stderr)

    print(log_text)


# ---------------------------------------------------------------------------
# Timezone helper  (stdlib only — no pytz / zoneinfo fallback for Python <3.9)
# ---------------------------------------------------------------------------

def resolve_timezone(tz_name: str) -> datetime.timezone:
    """
    Resolve a timezone string.
    Supports 'local', 'UTC', and fixed-offset strings like 'UTC+2', 'UTC-05:30'.
    On Python 3.9+ also supports IANA names via zoneinfo.
    """
    if tz_name.lower() in ("local", ""):
        return datetime.timezone(datetime.datetime.now().astimezone().utcoffset())

    if tz_name.upper() == "UTC":
        return datetime.timezone.utc

    # Fixed-offset: UTC+2, UTC-5, UTC+05:30
    fixed = re.fullmatch(r'UTC([+-])(\d{1,2})(?::(\d{2}))?', tz_name, re.IGNORECASE)
    if fixed:
        sign = 1 if fixed.group(1) == '+' else -1
        h = int(fixed.group(2))
        m = int(fixed.group(3) or 0)
        return datetime.timezone(datetime.timedelta(hours=sign * h, minutes=sign * m))

    # Try zoneinfo (Python 3.9+)
    try:
        from zoneinfo import ZoneInfo
        zi = ZoneInfo(tz_name)
        # Wrap in a fixed offset sampled at current time (safe for forensic use)
        now = datetime.datetime.now(tz=zi)
        return now.tzinfo  # type: ignore[return-value]
    except Exception:
        pass

    print(f"WARNING: Could not resolve timezone '{tz_name}'. Falling back to local time.", file=sys.stderr)
    return datetime.timezone(datetime.datetime.now().astimezone().utcoffset())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Rename files using their epoch timestamp to a readable datetime name.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("folder", help="Folder containing files to rename")
    parser.add_argument(
        "--timezone", default="local",
        help="Timezone for conversion (default: local). E.g. UTC, Europe/Oslo, UTC+2"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview renames without modifying any files"
    )
    parser.add_argument(
        "--log", default=None,
        help="Path to log file (default: rename_log.txt inside the target folder)"
    )

    args = parser.parse_args()

    folder = os.path.abspath(args.folder)
    tz = resolve_timezone(args.timezone)
    log_path = args.log or os.path.join(folder, "rename_log.txt")

    process_folder(folder, tz, args.dry_run, log_path)


if __name__ == "__main__":
    main()