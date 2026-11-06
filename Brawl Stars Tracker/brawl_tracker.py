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
- upgrade_log.csv         one row per upgrade the tracker notices between runs
                           (brawler unlocked, power level, gadget, star power,
                           hypercharge, buffie, prestige), with the time it
                           was first seen. Run `python brawl_tracker.py
                           --backfill-upgrades` once to seed it from the daily
                           snapshots that already exist.
- assets.json             icon lookup (game mode -> icon URL) built from the
                           public Brawlify API; failures here never fail a run.
"""

import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:  # only needed for talking to the API, not for --backfill-upgrades
    requests = None

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


# Transient failures worth retrying. The 52x codes are Cloudflare errors from
# the proxy sitting in front of Supercell's API (e.g. 525 = the proxy's own SSL
# handshake with its origin failed). They're not caused by anything in this
# project and normally clear up within seconds to a few minutes.
RETRYABLE_STATUS = {429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 525, 526, 527}
RETRY_DELAYS = [5, 15, 30, 60, 120]  # seconds to wait between attempts (6 attempts total)


def clean_error_body(resp):
    """Keep failure messages readable -- don't dump a whole HTML error page into the log."""
    text = resp.text.strip()
    if "<html" in text[:300].lower() or text.lower().startswith("<!doctype"):
        return "(HTML error page from the proxy/CDN)"
    return text[:300]


def api_get(path, token):
    url = f"{BASE_URL}{path}"
    last_problem = None

    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        except (requests.ConnectionError, requests.Timeout) as e:
            last_problem = f"network error ({type(e).__name__})"
        else:
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code not in RETRYABLE_STATUS:
                # Not transient (bad token, wrong tag, ...) -- retrying can't help.
                sys.exit(f"API error {resp.status_code} calling {path}: {clean_error_body(resp)}")
            last_problem = f"HTTP {resp.status_code}"

        if attempt < len(RETRY_DELAYS):
            delay = RETRY_DELAYS[attempt]
            print(f"{path}: {last_problem}; retrying in {delay}s "
                  f"(retry {attempt + 1}/{len(RETRY_DELAYS)})...")
            time.sleep(delay)

    sys.exit(
        f"API call to {path} still failing after {len(RETRY_DELAYS) + 1} attempts "
        f"({last_problem}). This is usually the proxy or Supercell's API having a bad "
        f"moment -- re-run the workflow later."
    )


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


def write_daily_snapshot_csv(path, header, new_rows, key_fn):
    """
    For periodic snapshot files (one entry expected per day, as opposed to
    battle_log.csv's one-entry-per-event model): replace any existing row(s)
    whose key matches one of new_rows' keys, then append new_rows. This means
    running the tracker multiple times in the same day (e.g. while testing)
    overwrites that day's snapshot instead of creating duplicates that distort
    the trend charts.

    Call ensure_header(path, header) before this, so the file's existing rows
    (if any) are already guaranteed to match the current column layout.

    key_fn(row) -> hashable key, e.g. the calendar date, or (date, brawler_id)
    for files with multiple rows per snapshot.
    """
    existing = []
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            existing_rows = list(csv.reader(f))
        if existing_rows:
            existing = existing_rows[1:]  # drop header

    # Keys are compared as strings: new rows carry real numbers (e.g. brawler_id as an int)
    # while rows read back from the CSV are text, and 16000001 != "16000001". Without this
    # the same-day overwrite silently never matched and every run appended a duplicate.
    def norm_key(r):
        k = key_fn(r)
        return tuple(str(x) for x in k) if isinstance(k, tuple) else str(k)

    new_keys = {norm_key(r) for r in new_rows}
    kept = [r for r in existing if norm_key(r) not in new_keys]
    all_rows = kept + new_rows

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(all_rows)


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
            "gadgetNames": [g.get("name", "") for g in gadgets],
            "starPowerNames": [s.get("name", "") for s in star_powers],
            "hyperChargeNames": [h.get("name", "") for h in hypercharges],
            "gadgetIds": [g.get("id") for g in gadgets],
            "starPowerIds": [s.get("id") for s in star_powers],
            "hyperChargeIds": [h.get("id") for h in hypercharges],
        }
        total_gadgets += len(gadgets)
        total_star_powers += len(star_powers)
        total_hypercharges += len(hypercharges)

    # Diagnostic: any fields on catalog entries we don't use. If Supercell ever
    # exposes e.g. which brawlers have buffies here, it will show up in this list
    # (and in the workflow log) rather than being silently ignored.
    known_keys = {"id", "name", "gadgets", "starPowers", "hyperCharges", "hypercharges"}
    extra_keys = sorted({k for b in data.get("items", []) for k in b.keys()} - known_keys)
    if extra_keys:
        print(f"Catalog entries also carry fields we don't use yet: {extra_keys}")

    return {
        "total_brawlers": len(data.get("items", [])),
        "total_gadgets": total_gadgets,
        "total_star_powers": total_star_powers,
        "total_hypercharges": total_hypercharges,
        "hypercharge_data_available": total_hypercharges > 0,
        "unused_item_fields": extra_keys,
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
        "3v3_victories", "solo_victories", "duo_victories", "club_name", "synthetic",
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
        False,  # every row this script writes going forward is real, not backfilled
    ]
    write_daily_snapshot_csv(path, header, [row], key_fn=lambda r: r[0][:10])
    print(f"Logged account snapshot: {player.get('trophies')} trophies "
          f"across {len(player.get('brawlers', []))} brawlers.")


BRAWLER_HEADER = [
    "timestamp", "brawler_id", "brawler_name", "trophies", "highest_trophies",
    "power", "rank", "gadgets_owned", "star_powers_owned", "hypercharge_owned",
    "prestige_level", "current_win_streak", "max_win_streak",
    "buffy_gadget", "buffy_star_power", "buffy_hyper_charge",
    "gadget_names", "star_power_names", "hypercharge_names",
]


def build_brawler_rows(player, now_iso):
    rows = []
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

        rows.append([
            now_iso, b.get("id"), b.get("name"), b.get("trophies"), b.get("highestTrophies"),
            b.get("power"), b.get("rank"), len(gadgets), len(star_powers), len(hyper),
            b.get("prestigeLevel"), b.get("currentWinStreak"), b.get("maxWinStreak"),
            buffies.get("gadget", False), buffies.get("starPower", False), buffies.get("hyperCharge", False),
            gadget_names, star_power_names, hypercharge_names,
        ])
    return rows


def log_brawler_snapshots(rows):
    path = SCRIPT_DIR / "brawler_history.csv"
    ensure_header(path, BRAWLER_HEADER)
    # Keyed by (date, brawler_id) since each run writes one row per brawler --
    # only today's rows get replaced, every other day's history is untouched.
    write_daily_snapshot_csv(path, BRAWLER_HEADER, rows, key_fn=lambda r: (r[0][:10], r[1]))


# ---------------------------------------------------------------- upgrade events
UPGRADE_HEADER = [
    "detected_at", "date", "brawler_id", "brawler_name", "type", "detail",
    "from_value", "to_value", "source",
]


def _int(v):
    if v is None or isinstance(v, bool):
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _flag(v):
    """True / False, or None when the value is blank (the column didn't exist yet)."""
    if isinstance(v, bool):
        return v
    s = "" if v is None else str(v).strip().lower()
    if s == "true":
        return True
    if s == "false":
        return False
    return None


def _split_names(v):
    return [n.strip() for n in str(v or "").split(";") if n.strip()]


def load_previous_brawler_state():
    """Latest stored row per brawler (keyed by brawler_id), or {} on the very first run."""
    path = SCRIPT_DIR / "brawler_history.csv"
    if not path.exists():
        return {}
    ensure_header(path, BRAWLER_HEADER)
    latest = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            bid = r.get("brawler_id")
            if not bid:
                continue
            if bid not in latest or r["timestamp"] >= latest[bid]["timestamp"]:
                latest[bid] = r
    return latest


def diff_brawler_states(prev_by_id, new_rows, detected_at, source="live"):
    """
    Compare the previous stored state with a new snapshot and describe what got
    upgraded in between. Works on dict rows (keys = BRAWLER_HEADER) so the live
    run and the one-off backfill share the exact same logic.

    A field that was blank in the previous row (the column didn't exist yet) is
    never treated as "just obtained" -- we only report changes we can actually see.
    """
    events = []
    if not prev_by_id:
        return events  # first-ever snapshot is just a baseline
    date = detected_at[:10]

    def ev(r, typ, detail, frm, to):
        events.append([detected_at, date, r["brawler_id"], r["brawler_name"], typ, detail, frm, to, source])

    for r in new_rows:
        p = prev_by_id.get(str(r["brawler_id"]))
        if p is None:
            ev(r, "unlock", "Brawler unlocked", "", "")
            continue

        old_power, new_power = _int(p.get("power")), _int(r.get("power"))
        if old_power is not None and new_power is not None and new_power > old_power:
            ev(r, "power", f"Power {old_power} \u2192 {new_power}", old_power, new_power)

        for typ, count_col, names_col, label in (
            ("gadget", "gadgets_owned", "gadget_names", "gadget"),
            ("star_power", "star_powers_owned", "star_power_names", "star power"),
            ("hypercharge", "hypercharge_owned", "hypercharge_names", "hypercharge"),
        ):
            old_n, new_n = _int(p.get(count_col)), _int(r.get(count_col))
            if old_n is None or new_n is None or new_n <= old_n:
                continue
            old_names = _split_names(p.get(names_col))
            gained = [n for n in _split_names(r.get(names_col)) if n not in old_names]
            # Names are only trustworthy when the old row recorded them (or had none to record).
            if gained and (old_names or old_n == 0):
                detail = ", ".join(gained)
            else:
                diff = new_n - old_n
                detail = f"+{diff} {label}{'s' if diff > 1 else ''}"
            ev(r, typ, detail, old_n, new_n)

        for col, label in (("buffy_gadget", "Gadget buffie"),
                           ("buffy_star_power", "Star buffie"),
                           ("buffy_hyper_charge", "Hyper buffie")):
            if _flag(p.get(col)) is False and _flag(r.get(col)) is True:
                ev(r, "buffie", label, "False", "True")

        old_pr, new_pr = _int(p.get("prestige_level")), _int(r.get("prestige_level"))
        if old_pr is not None and new_pr is not None and new_pr > old_pr:
            ev(r, "prestige", f"Prestige {old_pr} \u2192 {new_pr}", old_pr, new_pr)

    events.sort(key=lambda e: (e[3], e[4]))
    return events


def append_upgrade_events(events):
    if not events:
        print("No new upgrades since last run.")
        return
    path = SCRIPT_DIR / "upgrade_log.csv"
    ensure_header(path, UPGRADE_HEADER)
    for e in events:
        append_csv(path, UPGRADE_HEADER, e)
    print(f"Logged {len(events)} new upgrade(s): "
          + ", ".join(f"{e[3]} ({e[4]})" for e in events[:8]) + ("..." if len(events) > 8 else ""))


def backfill_upgrade_log(force=False):
    """
    One-off: rebuild upgrade_log.csv from the daily snapshots already stored in
    brawler_history.csv. Events are dated to the first daily snapshot that showed
    them (source = "backfill"), so their precision is one day.
    """
    src_path = SCRIPT_DIR / "brawler_history.csv"
    dst_path = SCRIPT_DIR / "upgrade_log.csv"
    if not src_path.exists():
        sys.exit("brawler_history.csv not found in this folder.")
    if dst_path.exists() and not force:
        sys.exit("upgrade_log.csv already exists. Re-run with --force to rebuild it from the daily snapshots.")
    ensure_header(src_path, BRAWLER_HEADER)

    by_day = {}
    with open(src_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            day_rows = by_day.setdefault(r["timestamp"][:10], {})
            cur = day_rows.get(r["brawler_id"])
            if cur is None or r["timestamp"] >= cur["timestamp"]:
                day_rows[r["brawler_id"]] = r

    days = sorted(by_day)
    events = []
    for prev_day, day in zip(days, days[1:]):
        detected_at = max(r["timestamp"] for r in by_day[day].values())
        events += diff_brawler_states(by_day[prev_day], list(by_day[day].values()), detected_at, source="backfill")

    with open(dst_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(UPGRADE_HEADER)
        writer.writerows(events)
    print(f"Backfilled {len(events)} upgrade(s) from {len(days)} daily snapshots into {dst_path.name}.")


# ---------------------------------------------------------------- icons (assets.json)
BRAWLAPI_GAMEMODES = "https://api.brawlapi.com/v1/gamemodes"

# Game modes the dashboard may show, plus whatever appears in battle_log.csv.
KNOWN_MODE_KEYS = [
    "soloShowdown", "duoShowdown", "trioShowdown", "gemGrab", "brawlBall", "bounty", "heist",
    "hotZone", "knockout", "duels", "wipeout", "lastStand", "payload", "bossFight", "roboRumble",
    "bigGame", "takedown", "volleyBrawl", "basketBrawl",
]

# battle-log key (normalised) -> other names to try in Brawlify's list (normalised), in order.
MODE_ALIASES = {
    "soloshowdown": ["showdown"],
    "duoshowdown": ["showdown"],
    "trioshowdown": ["showdown"],
}


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def match_mode_icons(mode_keys, gamemodes):
    """Map each battle-log mode key to an icon URL. Returns (urls, how_matched, unmatched)."""
    index = []
    for gm in gamemodes:
        terms = {_norm(gm.get("name", "")), _norm(gm.get("hash", ""))} - {""}
        url = gm.get("imageUrl") or gm.get("imageUrl2")
        if not url and gm.get("id") is not None:
            url = f"https://cdn.brawlify.com/game-modes/regular/{gm['id']}.png"
        if url and terms:
            index.append((terms, url))

    urls, how, unmatched = {}, {}, []
    for key in mode_keys:
        nk = _norm(key)
        found = None
        for terms, url in index:
            if nk in terms:
                found = (url, "exact")
                break
        if not found:
            for alias in MODE_ALIASES.get(nk, []):
                for terms, url in index:
                    if alias in terms:
                        found = (url, "alias")
                        break
                if found:
                    break
        if not found:
            # Last resort: the longest Brawlify name that is contained in the key (or vice versa).
            best = None
            for terms, url in index:
                for t in terms:
                    if len(t) >= 4 and (t in nk or nk in t):
                        if best is None or len(t) > best[0]:
                            best = (len(t), url)
            if best:
                found = (best[1], "fuzzy")
        if found:
            urls[key], how[key] = found
        else:
            unmatched.append(key)
    return urls, how, unmatched


def build_assets():
    """
    Write assets.json (mode -> icon URL) from the public Brawlify API. Brawler,
    gadget and star power icons need no lookup: the dashboard builds their URLs
    straight from the IDs the official API already gives us.
    Never fails the run -- if Brawlify is unreachable the previous file is kept.
    """
    path = SCRIPT_DIR / "assets.json"
    try:
        resp = requests.get(BRAWLAPI_GAMEMODES, headers={"User-Agent": "brawl-stats-tracker"}, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
        gamemodes = payload.get("list") if isinstance(payload, dict) else payload
        if not gamemodes:
            raise ValueError("response contained no game modes")
    except Exception as e:  # noqa: BLE001 -- icons are cosmetic, never worth failing a run
        print(f"Skipped icon lookup ({type(e).__name__}: {e}); keeping any existing assets.json.")
        return

    keys = list(KNOWN_MODE_KEYS)
    battle_path = SCRIPT_DIR / "battle_log.csv"
    if battle_path.exists():
        with open(battle_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("mode") and r["mode"] not in keys:
                    keys.append(r["mode"])

    urls, how, unmatched = match_mode_icons(keys, gamemodes)
    path.write_text(json.dumps({
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": BRAWLAPI_GAMEMODES,
        "modeIcons": urls,
        "modeMatch": how,
        "unmatchedModes": unmatched,
    }, indent=2), encoding="utf-8")
    print(f"Icons: matched {len(urls)}/{len(keys)} game modes"
          + (f"; no icon found for {unmatched}" if unmatched else "") + ".")
    fuzzy = [k for k, h in how.items() if h == "fuzzy"]
    if fuzzy:
        print(f"  (matched loosely, worth a glance: {fuzzy})")


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
    if "--backfill-upgrades" in sys.argv:
        backfill_upgrade_log(force="--force" in sys.argv)
        return

    if requests is None:
        sys.exit("Missing dependency. Run: pip install requests")
    token, raw_tag = load_config()
    tag = normalize_tag(raw_tag)
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    player = api_get(f"/players/{requests.utils.quote(tag)}", token)
    catalog = fetch_catalog(token)

    # Work out what changed BEFORE today's snapshot overwrites the previous state.
    new_brawler_rows = build_brawler_rows(player, now_iso)
    events = diff_brawler_states(
        load_previous_brawler_state(),
        [dict(zip(BRAWLER_HEADER, r)) for r in new_brawler_rows],
        now_iso,
    )

    log_player_snapshot(player, now_iso)
    log_brawler_snapshots(new_brawler_rows)
    write_catalog(catalog)
    log_battle_log(tag, token)
    append_upgrade_events(events)
    build_assets()


if __name__ == "__main__":
    main()
