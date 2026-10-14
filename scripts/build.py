"""Pull every regular-season White Sox box score from the MLB Stats API and
build season / last 10 / last 30 stat lines for hitters and pitchers.

Writes docs/data/sox.json, which the web page reads.
Run: python scripts/build.py            (picks the latest season with games)
     SEASON=2026 python scripts/build.py
"""

import json
import os
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone

API = "https://statsapi.mlb.com/api/v1"
TEAM_ID = int(os.environ.get("TEAM_ID", "145"))  # 145 = Chicago White Sox
OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "sox.json")
WINDOWS = {"season": None, "last30": 30, "last10": 10}

BAT_KEYS = ["plateAppearances", "atBats", "runs", "hits", "doubles", "triples",
            "homeRuns", "rbi", "baseOnBalls", "strikeOuts", "stolenBases",
            "caughtStealing", "hitByPitch", "sacFlies"]
PIT_KEYS = ["outs", "hits", "runs", "earnedRuns", "baseOnBalls", "strikeOuts",
            "homeRuns", "battersFaced", "wins", "losses", "saves", "holds"]


def get_json(url, tries=4):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "sox-stats"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def final_games(season):
    url = (f"{API}/schedule?sportId=1&teamId={TEAM_ID}&season={season}"
           f"&gameType=R")
    games = {}
    for d in get_json(url).get("dates", []):
        for g in d.get("games", []):
            if g["status"].get("abstractGameState") != "Final":
                continue
            if g["status"].get("detailedState") in ("Postponed", "Cancelled"):
                continue
            games[g["gamePk"]] = g  # dedupe resumed/suspended games
    return sorted(games.values(),
                  key=lambda g: (g["officialDate"], g.get("gameNumber", 1)))


def pick_season():
    if os.environ.get("SEASON"):
        return int(os.environ["SEASON"])
    year = datetime.now(timezone.utc).year
    return year if final_games(year) else year - 1


def num(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def parse_game(g):
    """Return (game summary, {player_id: line}) for the Sox side of one game."""
    box = get_json(f"{API}/game/{g['gamePk']}/boxscore")
    side = "home" if box["teams"]["home"]["team"]["id"] == TEAM_ID else "away"
    opp_side = "away" if side == "home" else "home"
    us, them = g["teams"][side], g["teams"][opp_side]
    summary = {
        "gamePk": g["gamePk"],
        "date": g["officialDate"],
        "opp": them["team"]["name"],
        "home": side == "home",
        "runs": us.get("score", 0),
        "runsAgainst": them.get("score", 0),
    }
    summary["win"] = summary["runs"] > summary["runsAgainst"]

    lines = {}
    for p in box["teams"][side]["players"].values():
        bat = p.get("stats", {}).get("batting", {}) or {}
        pit = p.get("stats", {}).get("pitching", {}) or {}
        if not bat and not pit:
            continue
        order = str(p.get("battingOrder", ""))
        lines[p["person"]["id"]] = {
            "name": p["person"]["fullName"],
            "pos": p.get("position", {}).get("abbreviation", ""),
            "started": order.isdigit() and int(order) % 100 == 0,
            "bat": {k: num(bat.get(k)) for k in BAT_KEYS} if bat else None,
            "pit": ({k: num(pit.get(k)) for k in PIT_KEYS}
                    | {"gamesStarted": num(pit.get("gamesStarted"))})
                   if pit and num(pit.get("battersFaced")) else None,
        }
    return summary, lines


def rate(n, d, digits=3):
    return round(n / d, digits) if d else None


def hitter_row(name, pos, games, started, t):
    obp_den = t["atBats"] + t["baseOnBalls"] + t["hitByPitch"] + t["sacFlies"]
    tb = (t["hits"] + t["doubles"] + 2 * t["triples"] + 3 * t["homeRuns"])
    avg = rate(t["hits"], t["atBats"])
    obp = rate(t["hits"] + t["baseOnBalls"] + t["hitByPitch"], obp_den)
    slg = rate(tb, t["atBats"])
    return {
        "name": name, "pos": pos, "G": games, "GS": started,
        "PA": t["plateAppearances"], "AB": t["atBats"], "R": t["runs"],
        "H": t["hits"], "2B": t["doubles"], "3B": t["triples"],
        "HR": t["homeRuns"], "RBI": t["rbi"], "BB": t["baseOnBalls"],
        "SO": t["strikeOuts"], "SB": t["stolenBases"],
        "AVG": avg, "OBP": obp, "SLG": slg,
        "OPS": round(obp + slg, 3) if obp is not None and slg is not None else None,
        "K%": rate(100 * t["strikeOuts"], t["plateAppearances"], 1),
        "BB%": rate(100 * t["baseOnBalls"], t["plateAppearances"], 1),
    }


def pitcher_row(name, games, t):
    outs = t["outs"]
    return {
        "name": name, "G": games, "GS": t["gamesStarted"],
        "W": t["wins"], "L": t["losses"], "SV": t["saves"], "HLD": t["holds"],
        "IP": f"{outs // 3}.{outs % 3}", "outs": outs,
        "H": t["hits"], "ER": t["earnedRuns"], "HR": t["homeRuns"],
        "BB": t["baseOnBalls"], "SO": t["strikeOuts"],
        "ERA": rate(27 * t["earnedRuns"], outs, 2),
        "WHIP": rate(3 * (t["hits"] + t["baseOnBalls"]), outs, 2),
        "K%": rate(100 * t["strikeOuts"], t["battersFaced"], 1),
        "BB%": rate(100 * t["baseOnBalls"], t["battersFaced"], 1),
    }


def build_window(games):
    names, positions = {}, defaultdict(Counter)
    bat_tot, pit_tot = defaultdict(Counter), defaultdict(Counter)
    bat_g, bat_gs, pit_g = Counter(), Counter(), Counter()
    for _, lines in games:
        for pid, ln in lines.items():
            names[pid] = ln["name"]
            if ln["bat"] and ln["bat"]["plateAppearances"] > 0:
                bat_tot[pid].update(ln["bat"])
                bat_g[pid] += 1
                bat_gs[pid] += ln["started"]
                if ln["pos"]:
                    positions[pid][ln["pos"]] += 1
            if ln["pit"]:
                pit_tot[pid].update(ln["pit"])
                pit_g[pid] += 1

    hitters = []
    for pid, t in bat_tot.items():
        pos = positions[pid].most_common(1)[0][0] if positions[pid] else ""
        if pos == "P":
            continue
        hitters.append({"id": pid} | hitter_row(names[pid], pos, bat_g[pid],
                                                 bat_gs[pid], t))
    pitchers = [{"id": pid} | pitcher_row(names[pid], pit_g[pid], t)
                for pid, t in pit_tot.items()]
    hitters.sort(key=lambda r: -r["PA"])
    pitchers.sort(key=lambda r: -r["outs"])

    wins = sum(1 for s, _ in games if s["win"])
    return {
        "games": len(games),
        "record": f"{wins}-{len(games) - wins}",
        "runs": sum(s["runs"] for s, _ in games),
        "runsAgainst": sum(s["runsAgainst"] for s, _ in games),
        "from": games[0][0]["date"] if games else None,
        "to": games[-1][0]["date"] if games else None,
        "hitters": hitters,
        "pitchers": pitchers,
    }


# American League leaderboard ranks shown next to season stats.
# MLB's leaderboards only rank qualified players for rate stats (AVG, ERA...),
# and tied players share a rank.
LEAGUE_ID = 103  # American League
RANK_TOP = 10    # only show a rank when a player is in the top 10
RANK_CATEGORIES = {
    "hitting": {"homeRuns": "HR", "hits": "H", "doubles": "2B", "runsBattedIn": "RBI",
                "baseOnBalls": "BB", "stolenBases": "SB", "battingAverage": "AVG",
                "onBasePercentage": "OBP", "sluggingPercentage": "SLG",
                "onBasePlusSlugging": "OPS"},
    "pitching": {"wins": "W", "saves": "SV", "inningsPitched": "IP",
                 "strikeouts": "SO", "earnedRunAverage": "ERA",
                 "walksAndHitsPerInningPitched": "WHIP"},
}


def league_ranks(season):
    """Return {"hitting"|"pitching": {player_id: {stat: "6" or "T-6"}}}."""
    ranks = {g: defaultdict(dict) for g in RANK_CATEGORIES}
    for group, cats in RANK_CATEGORIES.items():
        for cat, key in cats.items():
            url = (f"{API}/stats/leaders?leaderCategories={cat}&season={season}"
                   f"&leagueId={LEAGUE_ID}&sportId=1&statGroup={group}"
                   f"&limit={RANK_TOP}")
            try:
                block = get_json(url)["leagueLeaders"][0]["leaders"]
            except Exception as e:  # one bad category shouldn't stop the update
                print(f"  rank lookup failed for {cat}: {e}")
                continue
            counts = Counter(l["rank"] for l in block)
            for l in block:
                if l["rank"] > RANK_TOP:
                    continue
                tie = "T-" if counts[l["rank"]] > 1 else ""
                ranks[group][l["person"]["id"]][key] = f"{tie}{l['rank']}"
            time.sleep(0.1)
    return ranks


def main():
    season = pick_season()
    schedule = final_games(season)
    if not schedule:
        sys.exit(f"No final games found for {season}")
    print(f"{season}: {len(schedule)} final games")

    games = []
    for i, g in enumerate(schedule, 1):
        games.append(parse_game(g))
        if i % 25 == 0:
            print(f"  {i}/{len(schedule)} box scores")
        time.sleep(0.15)

    out = {
        "season": season,
        "team": TEAM_ID,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "windows": {k: build_window(games[-n:] if n else games)
                    for k, n in WINDOWS.items()},
        "log": [s for s, _ in games[-30:]],
        "rankTop": RANK_TOP,
    }
    ranks = league_ranks(season)
    for group, kind in (("hitting", "hitters"), ("pitching", "pitchers")):
        for row in out["windows"]["season"][kind]:
            if ranks[group].get(row["id"]):
                row["ranks"] = ranks[group][row["id"]]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
