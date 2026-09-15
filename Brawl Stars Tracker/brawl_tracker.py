#!/usr/bin/env python3
"""
Brawl Stars automated stat tracker.

Run this on a schedule (cron, Windows Task Scheduler, or GitHub Actions) and it
appends your current stats to CSV files every time it runs. Over time this
builds the exact history you want -- starting from whenever you first run it.

SETUP
-----
1. Get an API token:
   - Go to https://developer.brawlstars.com, log in, create a new key.
   - When asked to whitelist an IP, enter exactly: 128.128.128.128
     (This is not a mistake -- it's RoyaleAPI's proxy IP. Using their proxy
     endpoint below lets you call the API from ANY machine/IP without
     re-whitelisting every time your home IP or a cloud runner's IP changes.)
   - Copy the generated token.

2. Find your player tag in-game (Settings > top of profile, looks like #2ABC123).

3. Fill in config.json (created next to this script on first run) with your
   token and tag, OR set the environment variables BS_API_TOKEN and
   BS_PLAYER_TAG instead (useful for GitHub Actions secrets).

4. Install the one dependency:
   pip install requests --break-system-packages   (or just: pip install requests)

5. Run it once manually to test:
   python3 brawl_tracker.py

6. Schedule it to run automatically, e.g. every hour:
   - Linux/Mac (cron):   crontab -e   then add:
       0 * * * * /usr/bin/python3 /full/path/to/brawl_tracker.py
   - Windows: Task Scheduler > Create Basic Task > trigger hourly > action:
       run "python.exe" with argument "C:\\full\\path\\to\\brawl_tracker.py"
   - GitHub Actions: schedule a workflow with a cron trigger that checks out
     the repo, runs this script, and commits the updated CSVs back.

WHAT IT LOGS
------------
- brawl_history.csv       one row per run: timestamp, total trophies,
                           brawlers unlocked, highest trophies, etc.
- brawler_history.csv     one row per brawler per run: timestamp, brawler
                           name, trophies, highest trophies, power level.
- battle_log.csv          recent matches with their trophy change, deduped
                           by battle time -- this is how we backfill whatever
                           recent history the API still has (usually your
                           last ~25 battles) the very first time you run it.
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency. Run: pip install requests --break-system-packages")

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"

# Proxy base URL -- works from any IP once 128.128.128.128 is whitelisted on your token.
BASE_URL = "https://bsproxy.royaleapi.dev/v1"


def load_config():
    token = os.environ.get("BS_API_TOKEN")
    tag = os.environ.get("BS_PLAYER_TAG")

    if token and tag:
        return token, tag

    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(
            {"api_token": "PASTE_YOUR_TOKEN_HERE", "player_tag": "#YOURTAG"},
            indent=2
        ))
        sys.exit(
            f"Created {CONFIG_PATH.name} -- fill in your api_token and player_tag, "
            "then run this script again."
        )

    cfg = json.loads(CONFIG_PATH.read_text())
    token = cfg.get("api_token", "")
    tag = cfg.get("player_tag", "")

    if not token or token == "PASTE_YOUR_TOKEN_HERE" or not tag or tag == "#YOURTAG":
        sys.exit(f"Please fill in api_token and player_tag in {CONFIG_PATH.name}")

    return token, tag


def api_get(path, token):
    url = f"{BASE_URL}{path}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    if resp.status_code != 200:
        sys.exit(f"API error {resp.status_code} calling {path}: {resp.text[:300]}")
    return resp.json()


def normalize_tag(tag):
    tag = tag.strip().upper()
    if not tag.startswith("#"):
        tag = "#" + tag
    return tag


def append_csv(path, header, row):
    is_new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(header)
        writer.writerow(row)


def log_player_snapshot(player, now_iso):
    path = SCRIPT_DIR / "brawl_history.csv"
    header = [
        "timestamp", "total_trophies", "highest_trophies",
        "brawlers_unlocked", "3v3_victories", "solo_victories",
        "duo_victories", "club_name",
    ]
    row = [
        now_iso,
        player.get("trophies"),
        player.get("highestTrophies"),
        len(player.get("brawlers", [])),
        player.get("3vs3Victories"),
        player.get("soloVictories"),
        player.get("duoVictories"),
        (player.get("club") or {}).get("name", ""),
    ]
    append_csv(path, header, row)
    print(f"Logged account snapshot: {player.get('trophies')} trophies "
          f"across {len(player.get('brawlers', []))} brawlers.")


def log_brawler_snapshots(player, now_iso):
    path = SCRIPT_DIR / "brawler_history.csv"
    header = ["timestamp", "brawler_name", "trophies", "highest_trophies", "power"]
    for b in player.get("brawlers", []):
        row = [now_iso, b.get("name"), b.get("trophies"), b.get("highestTrophies"), b.get("power")]
        append_csv(path, header, row)


def log_battle_log(tag, token):
    """Pull recent battles and log any not already recorded (dedup by battleTime)."""
    path = SCRIPT_DIR / "battle_log.csv"

    seen_times = set()
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                seen_times.add(row["battle_time"])

    data = api_get(f"/players/{requests.utils.quote(tag)}/battlelog", token)
    header = ["battle_time", "mode", "map", "result_or_rank", "trophy_change"]

    new_count = 0
    for item in data.get("items", []):
        battle_time = item.get("battleTime")
        if battle_time in seen_times:
            continue
        battle = item.get("battle", {})
        row = [
            battle_time,
            battle.get("mode", ""),
            item.get("event", {}).get("map", ""),
            battle.get("result") or battle.get("rank", ""),
            battle.get("trophyChange", ""),
        ]
        append_csv(path, header, row)
        new_count += 1

    if new_count:
        print(f"Logged {new_count} new battle(s) from the recent battle log.")
    else:
        print("No new battles since last check.")


def main():
    token, raw_tag = load_config()
    tag = normalize_tag(raw_tag)
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    player = api_get(f"/players/{requests.utils.quote(tag)}", token)
    log_player_snapshot(player, now_iso)
    log_brawler_snapshots(player, now_iso)
    log_battle_log(tag, token)


if __name__ == "__main__":
    main()
