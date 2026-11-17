"""The company he keeps: the most similar minor league hitters to a prospect, and what they became.

A "stop" is one player, one season, one level (A, A+, AA, AAA) with 200+ PA.
Every stat is measured against the player's own league that season, so a 25% strikeout
rate in 2006 and in 2026 aren't treated as the same thing.

Similarity, stop to stop: distance across overall bat (wRC+), strikeouts, walks, power and
steals, each in standard deviations at that level, plus a charge for each year of age gap.
Career to date: the prospect's stops are combined, weighted by playing time, with higher
levels counting a bit more. A comp has to have played the prospect's top level within a
year of the same age; an earlier stop he doesn't have (skipped the level, or under 200 PA)
is charged a flat penalty.

Outcomes use the Harold-study tiers (best 3 seasons by Baseball-Reference WAR, 500+ MLB
at-bats), plus two junk buckets: "Cup of coffee" (reached MLB, under 500 AB) and
"Never made it". Only comps old enough for a career to play out are scored; newer ones are
listed separately as too soon to call.

Usage: python3 analysis/company.py PLAYER_ID [PLAYER_ID ...]   -> analysis/company/<id>.json
"""
import json, os, sys
import numpy as np, pandas as pd

LEVELS = {"A": "a", "A+": "aplus", "AA": "aa", "AAA": "aaa"}
RANK = {"A": 0, "A+": 1, "AA": 2, "AAA": 3}
LEVEL_WT = {"A": 1.0, "A+": 1.25, "AA": 1.5, "AAA": 1.75}
CUTOFF = {"AAA": 2019, "AA": 2018, "A+": 2017, "A": 2016}   # last season a comp can be scored from
MIN_PA = 200
FEATS = {"wRCplus": 1.0, "K_rel": 1.0, "BB_rel": 0.7, "ISO_rel": 1.0, "SB_rel": 0.4}
AGE_COST = 1.2        # each year of age gap costs this many standard deviations
MISSING = 2.2         # flat charge for an earlier stop the comp doesn't have
MIN_AB, HAROLD_ID = 500, "baineha01"
TIER_CUTS = [(7.5, "MVP candidate"), (5, "All-Star"), (3, "Solid regular"), (2, "Borderline starter"),
             (1, "Role player"), (0.01, "Fringe")]
ORDER = ["MVP candidate", "All-Star", "Solid regular", "Borderline starter", "Role player", "Fringe",
         "Below replacement", "Cup of coffee", "Never made it"]
# rows of the fingerprint chart: key, label
FINGER = [("young", "Young for the level"), ("wRCplus", "Overall bat (wRC+)"), ("AVG", "Batting average"),
          ("OBP", "On-base"), ("ISO_rel", "Power (ISO)"), ("HR_rel", "Home run rate"),
          ("BB_rel", "Walk rate"), ("K_rel", "Strikeout rate"), ("SB_rel", "Steals"), ("BABIP", "BABIP (luck check)")]


def load():
    frames = []
    for lvl, f in LEVELS.items():
        d = pd.read_csv(f"data/history/{f}_hitting.csv.gz")
        d["level"] = lvl
        frames.append(d)
    m = pd.concat(frames, ignore_index=True)
    m = m[m.season != 2020]
    num = ["PA", "AB", "H", "2B", "3B", "HR", "BB", "IBB", "HBP", "SF", "R", "SO", "SB", "CS", "age"]
    for c in num: m[c] = pd.to_numeric(m[c], errors="coerce").fillna(0)
    m = m[(m.pos != "P") & (m.PA > 0)].copy()
    # Prospects only: drop minor league seasons after a player's first full MLB season (300+ PA).
    mlb = pd.read_csv("data/history/mlb_hitting.csv.gz", low_memory=False)
    for c in ["PA", "AB"]: mlb[c] = pd.to_numeric(mlb[c], errors="coerce").fillna(0)
    est = mlb[mlb.PA >= 300].groupby("player_id").season.min()
    m = m[~(m.season > m.player_id.map(est).fillna(9999))].copy()

    m["1B"] = m.H - m["2B"] - m["3B"] - m.HR
    m["uBB"] = m.BB - m.IBB
    m["raw"] = .69*m.uBB + .72*m.HBP + .89*m["1B"] + 1.27*m["2B"] + 1.62*m["3B"] + 2.10*m.HR
    m["den"] = m.AB + m.uBB + m.SF + m.HBP
    m["TB"] = m["1B"] + 2*m["2B"] + 3*m["3B"] + 4*m.HR
    m["agePA"] = m.age * m.PA
    m["on1"] = m["1B"] + m.BB + m.HBP                    # chances to steal, roughly
    m["bip"] = m.AB - m.SO - m.HR + m.SF
    key = ["level", "league", "season"]
    cols = ["raw", "den", "H", "BB", "HBP", "AB", "SF", "R", "PA", "agePA", "SO", "HR", "TB", "SB", "CS", "on1", "bip"]
    L = m.groupby(key)[cols].sum()
    L["obp"] = (L.H + L.BB + L.HBP) / (L.AB + L.BB + L.HBP + L.SF)
    L["scale"] = L.obp / (L.raw / L.den)
    L["rpa"] = L.R / L.PA
    L["lg_age"] = L.agePA / L.PA
    L["lgK"] = L.SO / L.PA
    L["lgBB"] = L.BB / L.PA
    L["lgISO"] = (L.TB - L.H) / L.AB
    L["lgHR"] = L.HR / L.PA
    L["lgSB"] = (L.SB + L.CS) / L.on1
    m = m.join(L[["obp", "scale", "rpa", "lg_age", "lgK", "lgBB", "lgISO", "lgHR", "lgSB"]], on=key)
    m = m[m.PA >= MIN_PA].copy()
    m["wOBA"] = m.raw / m.den * m.scale
    m["wRCplus"] = 100 * (((m.wOBA - m.obp) / 1.2) + m.rpa) / m.rpa
    m["K"] = m.SO / m.PA
    m["BBr"] = m.BB / m.PA
    m["AVG"] = m.H / m.AB
    m["OBP"] = (m.H + m.BB + m.HBP) / (m.AB + m.BB + m.HBP + m.SF)
    m["SLG"] = m.TB / m.AB
    m["ISO"] = m.SLG - m.AVG
    m["BABIP"] = (m.H - m.HR) / m.bip.replace(0, np.nan)
    m["K_rel"] = 100 * m.K / m.lgK
    m["BB_rel"] = 100 * m.BBr / m.lgBB
    m["ISO_rel"] = 100 * m.ISO / m.lgISO
    m["HR_rel"] = 100 * (m.HR / m.PA) / m.lgHR
    m["SB_rel"] = 100 * ((m.SB + m.CS) / m.on1.replace(0, np.nan)) / m.lgSB
    m["SB_rel"] = m.SB_rel.fillna(0).clip(upper=500)
    m["age_rel"] = m.age - m.lg_age
    m["young"] = -m.age_rel
    # standard deviations and percentiles within each level, all seasons pooled
    for f in FEATS:
        g = m.groupby("level")[f]
        m["z_" + f] = (m[f] - g.transform("mean")) / g.transform("std")
    for k, _ in FINGER:
        m["p_" + k] = (m.groupby("level")[k].rank(pct=True) * 100).round()
    return m.reset_index(drop=True), mlb


def outcomes(mlb):
    w = pd.read_csv("data/history/war_batting.csv.gz", low_memory=False)
    for c in ["WAR", "PA", "G"]: w[c] = pd.to_numeric(w[c], errors="coerce").fillna(0)
    w = w[w.pitcher != "Y"]
    s = w.groupby(["mlb_ID", "player_ID", "year_ID"], as_index=False).agg(WAR=("WAR", "sum"))
    harold = round(float(s[s.player_ID == HAROLD_ID].WAR.sum()), 1)
    latest = int(s.year_ID.max())
    def car(g):
        q = g.WAR.sort_values(ascending=False).head(3).tolist()
        return pd.Series(dict(career_war=round(float(g.WAR.sum()), 1),
                              best3=round(float(np.mean(q + [0.0] * (3 - len(q)))), 2),
                              last=int(g.year_ID.max())))
    c = s.groupby("mlb_ID").apply(car, include_groups=False)
    ab = mlb.groupby("player_id").AB.sum()
    mlb_ids = set(mlb.player_id)
    def out(pid):
        if pid not in mlb_ids:
            return dict(tier="Never made it", war=None, best3=None, harold=False, active=False)
        a = float(ab.get(pid, 0))
        r = c.loc[pid] if pid in c.index else None
        war = None if r is None else float(r.career_war)
        best3 = None if r is None else float(r.best3)
        active = bool(r is not None and int(r["last"]) == latest)
        if a < MIN_AB or r is None:
            return dict(tier="Cup of coffee", war=war, best3=best3, harold=False, active=active, ab=int(a))
        t = next((n for cut, n in TIER_CUTS if best3 >= cut), "Below replacement")
        if war < 0: t = "Below replacement"
        return dict(tier=t, war=war, best3=best3, harold=bool(war >= harold), active=active, ab=int(a))
    return out, harold, latest


def stop_dict(r):
    d = dict(level=r.level, season=int(r.season), age=int(r.age), team=r.team, pos=r.pos, PA=int(r.PA),
             AVG=round(r.AVG, 3), OBP=round(r.OBP, 3), SLG=round(r.SLG, 3), HR=int(r.HR), SB=int(r.SB),
             K=round(100 * r.K, 1), BB=round(100 * r.BBr, 1), ISO=round(r.ISO, 3), BABIP=round(r.BABIP, 3),
             wRC=int(round(r.wRCplus)), age_rel=round(r.age_rel, 1))
    d["pct"] = {k: int(r["p_" + k]) for k, _ in FINGER}
    return d


def company(pid, m, out, n_named=10, n_wide=50, n_recent=6):
    me = m[m.player_id == pid].sort_values(["season", "level"], key=lambda s: s.map(RANK) if s.name == "level" else s)
    if me.empty: raise SystemExit(f"{pid}: no minor league stop with {MIN_PA}+ PA")
    last = me[me.season == me.season.max()]
    anchor = last.loc[last.level.map(RANK).idxmax()]
    stops = [r for _, r in me.iterrows()]
    wts = np.array([r.PA * LEVEL_WT[r.level] for r in stops], float)
    wts /= wts.sum()
    zc = ["z_" + f for f in FEATS]
    fw = np.array(list(FEATS.values()))

    def dist_to(r, pool):
        """distance from target stop r to every row in pool (same level)"""
        dz = (pool[zc].values - r[zc].values.astype(float)) * fw
        return np.sqrt((dz ** 2).sum(1) + (AGE_COST * (pool.age.values - r.age)) ** 2)

    others = m[m.player_id != pid]
    # candidates: have the anchor level within a year of the same age
    a_pool = others[(others.level == anchor.level) & ((others.age - anchor.age).abs() <= 1)].copy()
    a_pool["d"] = dist_to(anchor, a_pool)
    a_best = a_pool.sort_values("d").drop_duplicates("player_id").set_index("player_id")
    total = np.zeros(len(a_best))
    per_stop = {}
    for r, wt in zip(stops, wts):
        if r.name == anchor.name:
            d = a_best.d
        else:
            p = others[(others.level == r.level) & ((others.age - r.age).abs() <= 1)
                       & others.player_id.isin(a_best.index)].copy()
            p["d"] = dist_to(r, p)
            d = p.sort_values("d").drop_duplicates("player_id").set_index("player_id").d
            d = d.reindex(a_best.index).fillna(MISSING)
        per_stop[(r.level, int(r.season))] = d
        total += wt * d.values ** 2
    a_best["score"] = np.sqrt(total)
    a_best = a_best.sort_values("score")
    a_best["mature"] = a_best.season <= CUTOFF[anchor.level]

    def card(pidc, row):
        o = out(pidc)
        mine = m[m.player_id == pidc]
        d = dict(id=int(pidc), name=row["name"], pos=row.pos, score=round(float(row.score), 2), **o)
        d["stops"] = {}
        for r in stops:   # the comp's own line at each of the prospect's levels (closest in age)
            c = mine[(mine.level == r.level) & ((mine.age - r.age).abs() <= 1)]
            if len(c):
                c = c.assign(g=(c.age - r.age).abs()).sort_values(["g", "PA"], ascending=[True, False]).iloc[0]
                d["stops"][r.level + str(int(r.season))] = stop_dict(c)
        return d

    mature = a_best[a_best.mature]
    named = [card(i, r) for i, r in mature.head(n_named).iterrows()]
    wide = [out(i)["tier"] for i in mature.head(n_wide).index]
    recent = [card(i, r) for i, r in a_best[~a_best.mature].head(n_recent).iterrows()]
    tally = lambda ts: {t: ts.count(t) for t in ORDER}
    return dict(
        id=int(pid), name=anchor["name"], anchor=dict(level=anchor.level, age=int(anchor.age), season=int(anchor.season)),
        stops=[dict(key=r.level + str(int(r.season)), weight=round(float(wt), 2), **stop_dict(r)) for r, wt in zip(stops, wts)],
        pool=dict(candidates=int(len(a_best)), scored=int(len(mature)), cutoff=CUTOFF[anchor.level]),
        comps=named, tally=tally([c["tier"] for c in named]),
        wide=dict(n=len(wide), tally=tally(wide)),
        recent=recent, order=ORDER, finger=FINGER)


if __name__ == "__main__":
    m, mlb = load()
    out, harold, latest = outcomes(mlb)
    os.makedirs("analysis/company", exist_ok=True)
    for arg in sys.argv[1:]:
        res = company(int(arg), m, out)
        res.update(harold=harold, latest=latest)
        json.dump(res, open(f"analysis/company/{arg}.json", "w"), indent=1, ensure_ascii=False)
        print(f"\n{res['name']}  anchor {res['anchor']}  pool {res['pool']}")
        for s in res["stops"]:
            print(f"  {s['season']} {s['level']:3s} age {s['age']} PA {s['PA']} {s['AVG']}/{s['OBP']}/{s['SLG']} HR {s['HR']} "
                  f"K {s['K']} BB {s['BB']} ISO {s['ISO']} wRC+ {s['wRC']} wt {s['weight']}  pct {s['pct']}")
        for c in res["comps"]:
            a = c["stops"].get(res["stops"][-1]["key"], {})
            print(f"  {c['score']:.2f} {c['name']:22s} {c['pos']:3s} {c['tier']:18s} WAR {c['war']} best3 {c['best3']} "
                  f"{'HAROLD ' if c['harold'] else ''}{'active ' if c['active'] else ''}| {a.get('season')} age {a.get('age')} "
                  f"wRC+ {a.get('wRC')} K {a.get('K')} BB {a.get('BB')} ISO {a.get('ISO')} | stops {list(c['stops'])}")
        print("  tally10:", {k: v for k, v in res["tally"].items() if v})
        print(f"  wide{res['wide']['n']}:", {k: v for k, v in res["wide"]["tally"].items() if v})
        print("  recent:", [(c["name"], c["score"], c["tier"]) for c in res["recent"]])
