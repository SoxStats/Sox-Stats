"""Download season stat lines for every player, MLB and minor leagues.

One row per player per season per level, with the player's age that season.
MLB:  1876 to the latest season.  MiLB: 2005 to the latest season.
Writes gzipped CSVs to data/history/ plus a coverage summary.

Run: python scripts/history.py
"""

import csv
import gzip
import io
import json
import os
import time
import urllib.request
from datetime import datetime, timezone

API = "https://statsapi.mlb.com/api/v1/stats"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "history")
PAGE = 2000

LEVELS = {  # sportId: label
    1: "MLB", 11: "AAA", 12: "AA", 13: "A+", 14: "A", 15: "A-", 16: "Rk",
}
FIRST_SEASON = {1: 1876}
MILB_FIRST = 2005

HIT_FIELDS = {
    "G": "gamesPlayed", "PA": "plateAppearances", "AB": "atBats", "R": "runs",
    "H": "hits", "2B": "doubles", "3B": "triples", "HR": "homeRuns", "RBI": "rbi",
    "BB": "baseOnBalls", "IBB": "intentionalWalks", "SO": "strikeOuts",
    "HBP": "hitByPitch", "SF": "sacFlies", "SB": "stolenBases",
    "CS": "caughtStealing",
}
PIT_FIELDS = {
    "G": "gamesPlayed", "GS": "gamesStarted", "W": "wins", "L": "losses",
    "SV": "saves", "H": "hits", "R": "runs", "ER": "earnedRuns", "HR": "homeRuns",
    "BB": "baseOnBalls", "SO": "strikeOuts", "HBP": "hitBatsmen",
    "BF": "battersFaced",
}
BASE = ["season", "level", "player_id", "name", "age", "team", "league", "pos",
        "num_teams"]


def get_json(url, tries=5):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "sox-stats"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(3 * (attempt + 1))


def outs_from_ip(ip):
    try:
        whole, _, part = str(ip).partition(".")
        return int(whole) * 3 + int(part or 0)
    except ValueError:
        return 0


def num(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return ""


def season_rows(sport, season, group):
    rows, offset = [], 0
    while True:
        url = (f"{API}?stats=season&group={group}&season={season}"
               f"&sportIds={sport}&playerPool=ALL&limit={PAGE}&offset={offset}")
        block = get_json(url)["stats"]
        block = block[0] if block else {"splits": [], "totalSplits": 0}
        splits = block.get("splits", [])
        for s in splits:
            st = s.get("stat", {})
            row = {
                "season": season, "level": LEVELS[sport],
                "player_id": s.get("player", {}).get("id"),
                "name": s.get("player", {}).get("fullName", ""),
                "age": num(st.get("age")),
                "team": s.get("team", {}).get("name", ""),
                "league": s.get("league", {}).get("name", ""),
                "pos": s.get("position", {}).get("abbreviation", ""),
                "num_teams": s.get("numTeams", 1),
            }
            fields = HIT_FIELDS if group == "hitting" else PIT_FIELDS
            row.update({k: num(st.get(v)) for k, v in fields.items()})
            if group == "pitching":
                row["outs"] = (num(st.get("outs")) if st.get("outs") is not None
                               else outs_from_ip(st.get("inningsPitched")))
            rows.append(row)
        offset += len(splits)
        if not splits or offset >= block.get("totalSplits", 0):
            return rows
        time.sleep(0.2)


def latest_season():
    year = datetime.now(timezone.utc).year
    probe = get_json(f"{API}?stats=season&group=hitting&season={year}"
                     f"&sportIds=1&playerPool=ALL&limit=1")["stats"]
    has = probe and probe[0].get("totalSplits", 0) > 0
    return year if has else year - 1


def main():
    os.makedirs(OUT, exist_ok=True)
    last = latest_season()
    coverage = []
    for group, fields in (("hitting", HIT_FIELDS), ("pitching", PIT_FIELDS)):
        cols = BASE + list(fields) + (["outs"] if group == "pitching" else [])
        for sport, label in LEVELS.items():
            first = FIRST_SEASON.get(sport, MILB_FIRST)
            path = os.path.join(OUT, f"{label.replace('+', 'plus').replace('-', 'minus').lower()}_{group}.csv.gz")
            n_total = 0
            # mtime=0 keeps the file identical when the data hasn't changed
            with io.TextIOWrapper(gzip.GzipFile(path, "wb", mtime=0),
                                  newline="") as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                for season in range(first, last + 1):
                    try:
                        rows = season_rows(sport, season, group)
                    except Exception as e:
                        print(f"  FAILED {label} {group} {season}: {e}")
                        coverage.append({"level": label, "group": group,
                                         "season": season, "rows": None})
                        continue
                    w.writerows(rows)
                    n_total += len(rows)
                    coverage.append({"level": label, "group": group,
                                     "season": season, "rows": len(rows)})
                    time.sleep(0.15)
            print(f"{label} {group}: {n_total} rows, {first}-{last}")

    with open(os.path.join(OUT, "coverage.json"), "w") as f:
        json.dump({"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "through": last, "coverage": coverage}, f)


if __name__ == "__main__":
    main()
