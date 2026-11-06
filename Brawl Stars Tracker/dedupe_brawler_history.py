#!/usr/bin/env python3
"""
One-time cleanup for brawler_history.csv.

Keeps only the most recent snapshot per (day, brawler) pair. If a brawler
only has one row on a given day, it's untouched -- that's not a duplicate.
If the whole file only spans a single calendar day, nothing is changed at
all (there's nothing meaningful to collapse).

Run this once, in the same folder as brawler_history.csv:
    python3 dedupe_brawler_history.py

Writes a backup to brawler_history_backup.csv before touching the original.
"""

import csv
import shutil
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent
SRC = SCRIPT_DIR / "brawler_history.csv"
BACKUP = SCRIPT_DIR / "brawler_history_backup.csv"


def main():
    if not SRC.exists():
        raise SystemExit(f"{SRC.name} not found in this folder.")

    with open(SRC, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    header = rows[0]
    data = rows[1:]

    distinct_days = {r[0][:10] for r in data}
    if len(distinct_days) <= 1:
        print(f"Only {len(distinct_days)} distinct day(s) found -- nothing to collapse, file left untouched.")
        return

    # Group by (date, brawler_id); keep the row with the latest timestamp in each group.
    latest = {}
    for r in data:
        date = r[0][:10]
        brawler_id = r[1]
        key = (date, brawler_id)
        if key not in latest or r[0] > latest[key][0]:
            latest[key] = r

    kept_rows = list(latest.values())
    # Keep chronological order: by timestamp, then brawler_id for stable same-day ordering.
    kept_rows.sort(key=lambda r: (r[0], r[1]))

    shutil.copy(SRC, BACKUP)
    print(f"Backed up original to {BACKUP.name}")

    with open(SRC, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(kept_rows)

    removed = len(data) - len(kept_rows)
    print(f"Kept {len(kept_rows)} rows, removed {removed} duplicate same-day snapshot(s) across {len(distinct_days)} days.")


if __name__ == "__main__":
    main()
