"""Download Baseball-Reference's season WAR files (hitters and pitchers).

Source: https://www.baseball-reference.com/data/ (war_daily_bat / war_daily_pitch).
Used for our own analysis, credited to Baseball-Reference. Rows join to the
MLB history files on mlb_ID = player_id.
Writes data/history/war_batting.csv.gz and war_pitching.csv.gz.
"""

import csv
import gzip
import io
import os
import time
import urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "history")
FILES = {
    "war_batting": ("https://www.baseball-reference.com/data/war_daily_bat.txt",
                    ["name_common", "age", "mlb_ID", "player_ID", "year_ID",
                     "team_ID", "stint_ID", "lg_ID", "PA", "G", "WAR",
                     "WAR_off", "WAR_def", "runs_bat", "runs_field",
                     "runs_position", "OPS_plus", "pitcher"]),
    "war_pitching": ("https://www.baseball-reference.com/data/war_daily_pitch.txt",
                     ["name_common", "age", "mlb_ID", "player_ID", "year_ID",
                      "team_ID", "stint_ID", "lg_ID", "G", "GS", "IPouts",
                      "WAR", "ERA_plus", "xRA", "RA"]),
}


def fetch(url, tries=5):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (sox-stats fan project)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            print(f"  attempt {attempt + 1} failed: {e}")
            if attempt == tries - 1:
                raise
            time.sleep(20 * (attempt + 1))


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, (url, keep) in FILES.items():
        rows = list(csv.DictReader(io.StringIO(fetch(url))))
        cols = [c for c in keep if rows and c in rows[0]]
        path = os.path.join(OUT, f"{name}.csv.gz")
        with io.TextIOWrapper(gzip.GzipFile(path, "wb", mtime=0), newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        years = [r["year_ID"] for r in rows if r.get("year_ID", "").isdigit()]
        print(f"{name}: {len(rows)} rows, {min(years)}-{max(years)}")
        time.sleep(5)


if __name__ == "__main__":
    main()
