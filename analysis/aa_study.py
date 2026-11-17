"""Can you see a great player coming from what he did in AA?

Pool: every hitter's FIRST season at AA with 200+ PA, 2005-2018 (2018 = 8+ years for careers
to play out). Seasons after a player was already an MLB regular are dropped (rehab, demotions).
Stats are league-relative (see company.py). Outcomes use the Harold-study tiers plus
"Cup of coffee" (MLB, under 500 AB) and "Never made it".
  Made it = Solid regular or better (best 3 seasons average 3+ WAR). Star = All-Star or better.
Usage: python3 analysis/aa_study.py [PLAYER_ID]   -> analysis/aa_study.json
"""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "analysis")
import company as C

LAST = 2018
AGE_GROUPS = [(-99, -2.5, "3+ years young"), (-2.5, -1.5, "2 years young"), (-1.5, -0.5, "1 year young"),
              (-0.5, 0.5, "About league age"), (0.5, 99, "Older")]
STARS = {"MVP candidate", "All-Star"}
MADE = STARS | {"Solid regular"}

m, mlb = C.load()
out, harold, latest = C.outcomes(mlb)
aa = m[m.level == "AA"].sort_values("season")
first = aa.drop_duplicates("player_id").copy()               # first qualifying AA season
pool = first[first.season <= LAST].copy()
pool["agegrp"] = pd.cut(pool.age_rel, [g[0] for g in AGE_GROUPS] + [99], labels=[g[2] for g in AGE_GROUPS], right=False)
o = {pid: out(pid) for pid in pool.player_id}
pool["tier"] = pool.player_id.map(lambda p: o[p]["tier"])
pool["war"] = pool.player_id.map(lambda p: o[p]["war"])
pool["harold"] = pool.player_id.map(lambda p: o[p]["harold"])
pool["made"] = pool.tier.isin(MADE)
pool["star"] = pool.tier.isin(STARS)
pool["mlb"] = pool.tier != "Never made it"
pool["Kp"] = 100 * pool.K
pool["BBp"] = 100 * pool.BBr

def rate(s): return round(100 * float(s.mean()), 1) if len(s) else None

# ---------- 1. by age ----------
by_age = []
for _, _, g in AGE_GROUPS:
    d = pool[pool.agegrp == g]
    by_age.append(dict(group=g, n=len(d), mlb=rate(d.mlb), made=rate(d.made), star=rate(d.star),
                       harolds=int(d.harold.sum()), made_n=int(d.made.sum()), star_n=int(d.star.sum())))

# ---------- 2. what separates them, holding age steady ----------
# Within each age group, split every stat into thirds (low / middle / high), then pool the thirds
# across age groups. So "high K" means high for a hitter his age at AA.
STATS = [("wRCplus", "Overall bat (wRC+)"), ("ISO_rel", "Power (ISO)"), ("K_rel", "Strikeout rate"),
         ("BB_rel", "Walk rate"), ("AVG", "Batting average"), ("SB_rel", "Steals"), ("BABIP", "BABIP")]
young = pool[pool.age_rel < -0.5].copy()                    # 1+ years young: the prospects people argue about
def thirds(d, col):
    return d.groupby("agegrp", observed=True)[col].transform(lambda s: pd.qcut(s.rank(method="first"), 3, labels=["Low", "Middle", "High"]))
sep = []
for col, label in STATS:
    t = thirds(young, col)
    row = dict(stat=col, label=label)
    for b in ["Low", "Middle", "High"]:
        d = young[t == b]
        row[b] = dict(n=len(d), made=rate(d.made), star=rate(d.star))
    row["spread"] = round(abs(row["High"]["made"] - row["Low"]["made"]), 1)
    sep.append(row)
sep.sort(key=lambda r: -r["spread"])

# made it vs didn't, medians (young group)
def medians(d):
    return dict(n=len(d), wRC=round(d.wRCplus.median()), ISO=round(d.ISO.median(), 3), K=round(d.Kp.median(), 1),
                BB=round(d.BBp.median(), 1), AVG=round(d.AVG.median(), 3), BABIP=round(d.BABIP.median(), 3))
made_vs = dict(made=medians(young[young.made]), didnt=medians(young[~young.made & young.mlb]),
               never=medians(young[~young.mlb]))

# ---------- 3. Aaron's guess: young, raking, but striking out ----------
# 2+ years young with a 130+ wRC+ at AA, split by strikeout rate vs his league
rak = pool[(pool.age_rel < -1.5) & (pool.wRCplus >= 130)].copy()
rak["k_band"] = np.where(rak.K_rel >= 120, "Strikes out a lot (20%+ above league)",
                np.where(rak.K_rel <= 85, "Rarely strikes out (15%+ below league)", "About league average"))
kguess = []
for b in ["Rarely strikes out (15%+ below league)", "About league average", "Strikes out a lot (20%+ above league)"]:
    d = rak[rak.k_band == b]
    kguess.append(dict(band=b, n=len(d), made=rate(d.made), star=rate(d.star),
                       names_made=d[d.made].sort_values("war", ascending=False).name.head(6).tolist(),
                       names_bust=d[~d.made].sort_values("wRCplus", ascending=False).name.head(6).tolist()))

# ---------- 4. the next year ----------
nxt = m[m.level.isin(["AA", "AAA"])][["player_id", "season", "PA", "wRCplus", "ISO", "K", "BBr"]]
def next_line(r):
    d = nxt[(nxt.player_id == r.player_id) & (nxt.season == r.season + 1)]
    if d.empty: return None
    w = d.PA / d.PA.sum()
    return pd.Series(dict(n_wRC=(d.wRCplus * w).sum(), n_ISO=(d.ISO * w).sum(), n_K=100 * (d.K * w).sum(), n_BB=100 * (d.BBr * w).sum()))
yr = young.join(young.apply(next_line, axis=1))
mlb_next = mlb.assign(PA=pd.to_numeric(mlb.PA, errors="coerce")).groupby(["player_id", "season"]).PA.sum()
yr["mlb_next_pa"] = [float(mlb_next.get((p, s + 1), 0)) for p, s in zip(yr.player_id, yr.season)]
race = {}
for g, d in (("made", yr[yr.made]), ("didnt", yr[~yr.made])):
    h = d.dropna(subset=["n_wRC"])
    race[g] = dict(n=len(d), n_line=len(h), straight_up=rate(d.mlb_next_pa >= 200),
                   now_wRC=round(h.wRCplus.median()), next_wRC=round(h.n_wRC.median()),
                   now_ISO=round(h.ISO.median(), 3), next_ISO=round(h.n_ISO.median(), 3),
                   now_K=round(h.Kp.median(), 1), next_K=round(h.n_K.median(), 1),
                   now_BB=round(h.BBp.median(), 1), next_BB=round(h.n_BB.median(), 1),
                   held_wRC=rate(h.n_wRC >= h.wRCplus - 10))

res = dict(last=LAST, pool=len(pool), harold=harold, by_age=by_age, young_n=len(young),
           separators=sep, made_vs=made_vs, kguess=kguess, race=race)

# ---------- 5. a prospect on the same charts ----------
if len(sys.argv) > 1:
    pid = int(sys.argv[1])
    me = aa[aa.player_id == pid].iloc[0]
    g = next(lbl for lo, hi, lbl in AGE_GROUPS if lo <= me.age_rel < hi)
    peers = pool[pool.agegrp == g]
    pct = lambda col: round(100 * float((peers[col] < me[col]).mean()))
    res["player"] = dict(name=me["name"], season=int(me.season), age=int(me.age), age_rel=round(me.age_rel, 1), group=g,
                         wRC=round(me.wRCplus), ISO=round(me.ISO, 3), K=round(100 * me.K, 1), BB=round(100 * me.BBr, 1),
                         pct={col: pct(col) for col, _ in STATS}, peers=len(peers),
                         raking=bool(me.age_rel < -1.5 and me.wRCplus >= 130),
                         k_band=("Strikes out a lot (20%+ above league)" if me.K_rel >= 120 else
                                 "Rarely strikes out (15%+ below league)" if me.K_rel <= 85 else "About league average"),
                         K_rel=round(me.K_rel))

def clean(x):
    if isinstance(x, dict): return {k: clean(v) for k, v in x.items()}
    if isinstance(x, list): return [clean(v) for v in x]
    if isinstance(x, (np.floating,)): return float(x)
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, np.bool_): return bool(x)
    return x
res = clean(res)
json.dump(res, open("analysis/aa_study.json", "w"), indent=1, ensure_ascii=False)
pool[["player_id", "name", "season", "age", "age_rel", "agegrp", "PA", "wRCplus", "ISO", "Kp", "BBp", "K_rel", "tier", "war", "harold"]] \
    .to_csv("analysis/aa_study.csv", index=False)
print(f"pool {len(pool)} first AA seasons 2005-{LAST}; young (1+ yr) {len(young)}")
for r in by_age: print(" ", r)
print("separators (young, made-it % low/mid/high third):")
for r in sep: print(f"  {r['label']:22s} low {r['Low']['made']:5} mid {r['Middle']['made']:5} high {r['High']['made']:5}  stars {r['Low']['star']}/{r['Middle']['star']}/{r['High']['star']}  spread {r['spread']}")
print("made vs:", made_vs)
for r in kguess: print("  K guess:", r)
print("race:", race)
if "player" in res: print("player:", res["player"])
