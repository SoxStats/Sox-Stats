"""Download Statcast plate-discipline numbers for every hitter, 2015 to the latest season.

Source: Baseball Savant custom leaderboard (CSV). One row per hitter per season (min 50 PA).
Columns: season, player_id, name, pa, k_percent, bb_percent, chase (oz_swing_percent),
whiff (whiff_percent), z_contact (z_contact_percent), contact (iz+oz contact).
Writes data/history/savant_batting.csv.gz.
"""
import csv, gzip, io, os, time, urllib.request
from datetime import datetime, timezone

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "history", "savant_batting.csv.gz")
SEL = "pa,k_percent,bb_percent,oz_swing_percent,whiff_percent,z_contact_percent,iz_contact_percent,oz_contact_percent"
URL = ("https://baseballsavant.mlb.com/leaderboard/custom?year={y}&type=batter&filter=&min=50"
       "&selections=" + SEL + "&chart=false&x=pa&y=pa&r=no&chartType=beeswarm&sort=pa&sortDir=desc&csv=true")


def fetch(url, tries=5):
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (sox-stats fan project)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read().decode("utf-8-sig", "replace")
        except Exception as e:
            print(f"  attempt {a+1} failed: {e}")
            if a == tries - 1:
                raise
            time.sleep(15 * (a + 1))


def main():
    last = datetime.now(timezone.utc).year
    cols = ["season", "player_id", "name", "pa", "k_percent", "bb_percent", "chase", "whiff",
            "z_contact", "iz_contact", "oz_contact"]
    with io.TextIOWrapper(gzip.GzipFile(OUT, "wb", mtime=0), newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for y in range(2015, last + 1):
            rows = list(csv.DictReader(io.StringIO(fetch(URL.format(y=y)))))
            if not rows:
                print(y, "no rows"); continue
            namecol = next((c for c in rows[0] if "name" in c.lower()), None)
            for r in rows:
                w.writerow([y, r.get("player_id"), r.get(namecol, ""), r.get("pa"), r.get("k_percent"),
                            r.get("bb_percent"), r.get("oz_swing_percent"), r.get("whiff_percent"),
                            r.get("z_contact_percent"), r.get("iz_contact_percent"), r.get("oz_contact_percent")])
            print(y, len(rows), "hitters; columns:", list(rows[0])[:12])
            time.sleep(3)


if __name__ == "__main__":
    main()
