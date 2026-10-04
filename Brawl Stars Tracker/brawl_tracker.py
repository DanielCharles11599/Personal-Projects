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

6. Schedule it to run automatically (see GitHub Actions workflow, or cron /
   Task Scheduler on your own machine).

WHAT IT LOGS
------------
- brawl_history.csv       one row per run: account-level snapshot (trophies,
                           brawlers unlocked, victories, account level, etc).
- brawler_history.csv     one row per brawler per run: trophies, power, the
                           game's own rank badge, and gadget/star power/
                           hypercharge counts owned for that brawler.
- battle_log.csv          recent matches with brawler used, outcome, and
                           trophy change, deduped by battle time.
- catalog.json            NOT historical -- overwritten every run with the
                           current full game catalog (every brawler, and how
                           many gadgets/star powers/hypercharges each one
                           has), used by the dashboard to compute "X out of
                           total" completion stats.
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


def ensure_header(path, header):
    """
    Call once per file per run, before any append_csv() calls for it.

    If the file already exists with an older header that's simply a prefix of
    the current one (i.e. we only ever added columns at the end, which is how
    every schema change here has happened so far), migrate it in place: pad
    every existing row with blanks for the new trailing columns, under the
    new header. This is what was missing before -- a header mismatch used to
    silently misalign every column (e.g. a victory count landing in the
    club_name field) instead of being caught or fixed.

    If the header changed in some other way (columns removed/reordered), this
    refuses to guess and fails loudly instead, since silent corruption is far
    worse than a visible error on a scheduled run.
    """
    if not path.exists():
        return
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        return
    old_header = rows[0]
    if old_header == header:
        return
    if len(header) > len(old_header) and header[:len(old_header)] == old_header:
        extra = len(header) - len(old_header)
        migrated = [r + [""] * extra for r in rows[1:]]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(migrated)
        print(f"Migrated {path.name} to the current schema ({extra} new column(s)); existing rows preserved.")
    else:
        sys.exit(
            f"{path.name}'s header doesn't match the current schema and isn't a simple "
            f"column addition, so it can't be auto-migrated safely.\n"
            f"Existing header: {old_header}\nExpected header:  {header}\n"
            f"Back up and delete this file so it can regenerate cleanly."
        )


def append_csv(path, header, row):
    is_new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(header)
        writer.writerow(row)


def fetch_catalog(token):
    """
    Pull the full game catalog (every brawler currently in the game) so the
    dashboard can compute "X out of total" completion stats. Overwritten
    fresh every run -- not historical.
    """
    data = api_get("/brawlers", token)
    catalog = {}
    total_gadgets = 0
    total_star_powers = 0
    total_hypercharges = 0

    for b in data.get("items", []):
        gadgets = b.get("gadgets", []) or []
        star_powers = b.get("starPowers", []) or []
        # Hypercharges aren't confirmed in the official /brawlers schema as of
        # this script's writing. Checked defensively under both possible key
        # spellings -- if Supercell has added this, it'll just start working.
        hypercharges = b.get("hyperCharges") or b.get("hypercharges") or []

        catalog[str(b.get("id"))] = {
            "name": b.get("name"),
            "gadgets": len(gadgets),
            "starPowers": len(star_powers),
            "hyperCharges": len(hypercharges),
        }
        total_gadgets += len(gadgets)
        total_star_powers += len(star_powers)
        total_hypercharges += len(hypercharges)

    return {
        "total_brawlers": len(data.get("items", [])),
        "total_gadgets": total_gadgets,
        "total_star_powers": total_star_powers,
        "total_hypercharges": total_hypercharges,
        "hypercharge_data_available": total_hypercharges > 0,
        "brawlers": catalog,
    }


def write_catalog(catalog):
    path = SCRIPT_DIR / "catalog.json"
    path.write_text(json.dumps(catalog, indent=2))
    print(f"Catalog updated: {catalog['total_brawlers']} brawlers, "
          f"{catalog['total_gadgets']} gadgets, {catalog['total_star_powers']} star powers.")


def log_player_snapshot(player, now_iso):
    path = SCRIPT_DIR / "brawl_history.csv"
    header = [
        "timestamp", "total_trophies", "highest_trophies",
        "brawlers_unlocked", "exp_level", "total_prestige_level",
        "3v3_victories", "solo_victories", "duo_victories", "club_name",
    ]
    ensure_header(path, header)
    row = [
        now_iso,
        player.get("trophies"),
        player.get("highestTrophies"),
        len(player.get("brawlers", [])),
        player.get("expLevel"),
        player.get("totalPrestigeLevel"),
        player.get("3vs3Victories"),
        player.get("soloVictories"),
        player.get("duoVictories"),
        (player.get("club") or {}).get("name", ""),
    ]
    append_csv(path, header, row)
    print(f"Logged account snapshot: {player.get('trophies')} trophies "
          f"across {len(player.get('brawlers', []))} brawlers.")


def log_brawler_snapshots(player, now_iso, catalog):
    path = SCRIPT_DIR / "brawler_history.csv"
    header = [
        "timestamp", "brawler_id", "brawler_name", "trophies", "highest_trophies",
        "power", "rank", "gadgets_owned", "star_powers_owned", "hypercharge_owned",
        "prestige_level", "current_win_streak", "max_win_streak",
        "buffy_gadget", "buffy_star_power", "buffy_hyper_charge",
        "gadget_names", "star_power_names", "hypercharge_names",
    ]
    ensure_header(path, header)

    for b in player.get("brawlers", []):
        gadgets = b.get("gadgets", []) or []
        star_powers = b.get("starPowers", []) or []
        hyper = b.get("hyperCharges") or b.get("hypercharges") or []
        if not isinstance(hyper, list):
            hyper = []
        buffies = b.get("buffies") or {}

        # Semicolon-joined since names themselves may contain commas/spaces.
        gadget_names = ";".join(g.get("name", "") for g in gadgets)
        star_power_names = ";".join(s.get("name", "") for s in star_powers)
        hypercharge_names = ";".join(h.get("name", "") for h in hyper)

        row = [
            now_iso, b.get("id"), b.get("name"), b.get("trophies"), b.get("highestTrophies"),
            b.get("power"), b.get("rank"), len(gadgets), len(star_powers), len(hyper),
            b.get("prestigeLevel"), b.get("currentWinStreak"), b.get("maxWinStreak"),
            buffies.get("gadget", False), buffies.get("starPower", False), buffies.get("hyperCharge", False),
            gadget_names, star_power_names, hypercharge_names,
        ]
        append_csv(path, header, row)


def find_own_brawler(battle, own_tag):
    """Look through a battle's teams/players for our own tag and return the brawler we used."""
    own_tag = own_tag.upper()
    entries = []
    for team in battle.get("teams", []) or []:
        entries.extend(team)
    entries.extend(battle.get("players", []) or [])

    for p in entries:
        if (p.get("tag") or "").upper() == own_tag:
            return (p.get("brawler") or {}).get("name", "")
    return ""


def determine_outcome(battle):
    """
    Normalize the result of a battle into a consistent outcome column.
    - Versus modes (3v3, duels, etc.) report battle['result']: victory/defeat/draw.
    - Showdown modes (solo/duo) report battle['rank'] instead -- there's no official
      win/loss label for these, so we keep the raw rank in its own column and leave
      'outcome' blank.
    """
    if "result" in battle:
        return battle.get("result", ""), ""
    if "rank" in battle:
        return "", battle.get("rank", "")
    return "", ""


def was_star_player(battle, own_tag):
    star = battle.get("starPlayer")
    if not star:
        return False
    return (star.get("tag") or "").upper() == own_tag.upper()


def log_battle_log(tag, token):
    """Pull recent battles and log any not already recorded (dedup by battleTime)."""
    path = SCRIPT_DIR / "battle_log.csv"

    seen_times = set()
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                seen_times.add(row["battle_time"])

    data = api_get(f"/players/{requests.utils.quote(tag)}/battlelog", token)
    header = ["battle_time", "mode", "map", "brawler_used", "outcome", "rank",
              "trophy_change", "was_star_player"]
    ensure_header(path, header)

    new_count = 0
    for item in data.get("items", []):
        battle_time = item.get("battleTime")
        if battle_time in seen_times:
            continue
        battle = item.get("battle", {})
        outcome, rank = determine_outcome(battle)
        row = [
            battle_time,
            battle.get("mode", ""),
            item.get("event", {}).get("map", ""),
            find_own_brawler(battle, tag),
            outcome,
            rank,
            battle.get("trophyChange", ""),
            was_star_player(battle, tag),
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
    catalog = fetch_catalog(token)

    log_player_snapshot(player, now_iso)
    log_brawler_snapshots(player, now_iso, catalog)
    write_catalog(catalog)
    log_battle_log(tag, token)


if __name__ == "__main__":
    main()
