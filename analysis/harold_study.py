"""How rare is a Harold? Hitters who debuted 1990-2016, tiered on Baseball-Reference WAR.

Tier = average of a player's best 3 seasons by WAR, any playing time (the 500 AB filter already applies; missing seasons count as 0):
  MVP candidate 7.5+, All-Star 5+, Solid regular 3+, Just a guy above 0, Below replacement 0 or less.
Harold = Harold Baines's career bWAR. Chart baseline: 500+ career MLB at-bats.
Drafted vs international: birth country from the Lahman register (US, Canada, Puerto Rico
are in the draft; everyone else signs as an international free agent).
Usage: python3 analysis/harold_study.py [PEOPLE_CSV]  (default data/history/lahman_people.csv.gz, from the Lahman register)
"""
import json, sys
import numpy as np, pandas as pd

FIRST, LAST, MIN_PA, MIN_AB = 1990, 2016, 300, 500
CUTS = [(7.5, "MVP candidate"), (5, "All-Star"), (3, "Solid regular"), (0.01, "Just a guy")]
ORDER = ["MVP candidate", "All-Star", "Solid regular", "Just a guy", "Below replacement"]

def tier(v):
    for c, name in CUTS:
        if v >= c: return name
    return "Below replacement"

w = pd.read_csv("data/history/war_batting.csv.gz", low_memory=False)
for c in ["WAR", "PA", "G"]:
    w[c] = pd.to_numeric(w[c], errors="coerce").fillna(0)
hit = w[w.pitcher != "Y"]
season = hit.groupby(["mlb_ID", "player_ID", "name_common", "year_ID"], as_index=False).agg(
    WAR=("WAR", "sum"), PA=("PA", "sum"), G=("G", "sum"), age=("age", "first"))

HAROLD = round(float(season[season.player_ID == "baineha01"].WAR.sum()), 1)
LATEST = int(season.year_ID.max())

def career(g):
    q = g.WAR.sort_values(ascending=False).head(3).tolist()
    best3 = float(np.mean(q + [0.0] * (3 - len(q))))
    return pd.Series(dict(debut=int(g[g.G > 0].year_ID.min()), last=int(g.year_ID.max()),
                          career_war=round(float(g.WAR.sum()), 1), best3=round(best3, 2),
                          peak=round(float(g.WAR.max()), 1), age_now=g.age.max()))

car = season.groupby(["mlb_ID", "player_ID", "name_common"]).apply(career, include_groups=False).reset_index()
pool = car[(car.debut >= FIRST) & (car.debut <= LAST)].copy()

ab = pd.read_csv("data/history/mlb_hitting.csv.gz", usecols=["player_id", "AB"], low_memory=False)
ab["AB"] = pd.to_numeric(ab.AB, errors="coerce").fillna(0)
pool["AB"] = pool.mlb_ID.map(ab.groupby("player_id").AB.sum()).fillna(0).astype(int)

people = pd.read_csv(sys.argv[1] if len(sys.argv) > 1 else "data/history/lahman_people.csv.gz")
born = people.dropna(subset=["bbrefID"]).drop_duplicates("bbrefID").set_index("bbrefID").birthCountry
pool["born"] = pool.player_ID.map(born)
pool["route"] = np.where(pool.born.isin(["USA", "CAN", "P.R."]), "Drafted pool (US/CAN/PR)",
                np.where(pool.born.isna(), "Unknown", "International signing"))

pool["tier"] = pool.best3.map(tier)
pool["harold"] = pool.career_war >= HAROLD
pool["active"] = pool["last"] == LATEST
main = pool[pool.AB >= MIN_AB]
years = LAST - FIRST + 1

def counts(df):
    n = len(df)
    out = {t: int((df.tier == t).sum()) for t in ORDER}
    out.update(total=n, harolds=int(df.harold.sum()))
    out["one_in"] = {k: (round(n / v, 1) if v else None) for k, v in out.items() if k not in ("total",)}
    return out

# Still chasing: active, not yet a Harold, 20+ career WAR
chasing = pool[pool.active & ~pool.harold & (pool.career_war >= 20)].sort_values("career_war", ascending=False)

# Minors: position players who first reached High-A in 2005-2012 (minors data starts 2005;
# ending in 2012 gives the group 10+ years to play out). Big leaguers on rehab stints are
# excluded: a player only counts if he hadn't played in MLB before his first High-A season.
MILB_FIRST, MILB_LAST = 2005, 2012
a = pd.read_csv("data/history/aplus_hitting.csv.gz", usecols=["season", "player_id", "pos"], low_memory=False)
a = a[a.pos != "P"]
firstA = a.groupby("player_id").season.min()
mlb_first = season.groupby("mlb_ID").year_ID.min()
firstA = firstA[(firstA >= MILB_FIRST) & (firstA <= MILB_LAST)]
firstA = firstA[~(firstA.index.map(mlb_first).fillna(9999) < firstA.values)]
grp = car[car.mlb_ID.isin(firstA.index)].copy()
grp["AB"] = grp.mlb_ID.map(ab.groupby("player_id").AB.sum()).fillna(0)
milb = dict(cohort=f"first reached High-A {MILB_FIRST}-{MILB_LAST}",
            reached_high_a=int(len(firstA)), made_mlb=int(len(grp)),
            never_made_it=int(len(firstA) - len(grp)),
            got_500_ab=int((grp.AB >= MIN_AB).sum()),
            harolds=int((grp.career_war >= HAROLD).sum()),
            harold_names=grp[grp.career_war >= HAROLD].sort_values("career_war", ascending=False).name_common.tolist())

res = dict(
    harold_war=HAROLD, pool_years=f"{FIRST}-{LAST}", latest_season=LATEST,
    debuted=int(len(pool)), under_500_ab=int((pool.AB < MIN_AB).sum()),
    main=counts(main),
    per_year={k: round(v / years, 1) for k, v in counts(main).items() if isinstance(v, int)},
    by_route={r: counts(main[main.route == r]) for r in main.route.unique()},
    harold_list=main[main.harold].sort_values("career_war", ascending=False)[
        ["name_common", "debut", "career_war", "best3", "tier", "route", "active"]].to_dict("records"),
    chasing=chasing[["name_common", "debut", "career_war", "best3", "age_now"]].to_dict("records"),
    harold_not_star=main[main.harold & ~main.tier.isin(["MVP candidate", "All-Star"])][
        ["name_common", "career_war", "best3", "tier"]].to_dict("records"),
    star_not_harold=main[~main.harold & main.tier.isin(["MVP candidate", "All-Star"])][
        ["name_common", "career_war", "best3", "tier", "active"]].to_dict("records"),
    milb_since_2005=milb,
)
json.dump(res, open("analysis/harold_study.json", "w"), indent=1, default=str)
main.to_csv("analysis/harold_study.csv", index=False)
print(json.dumps({k: v for k, v in res.items() if k not in ("harold_list", "chasing", "harold_not_star", "star_not_harold")}, indent=1))
print("chasing:", [(r["name_common"], r["career_war"], r["age_now"]) for r in res["chasing"]])
print("harolds:", len(res["harold_list"]), "| star not harold:", len(res["star_not_harold"]), "| harold not star:", len(res["harold_not_star"]))
print("unknown route:", main[main.route == "Unknown"].name_common.tolist()[:20])
