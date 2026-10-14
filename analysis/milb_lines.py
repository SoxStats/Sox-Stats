"""Minor league 'prospect bars': where future regulars and stars sat at each level.

Each dot = one player at one level, all his seasons at that level combined (PA-weighted).
x = years younger/older than his league's average age, y = wRC+ against his league.
Color = how his MLB career turned out (best 3 seasons, same tiers as the Colson piece,
plus a 'just below regular' band at 2-3 WAR / 105-115 wRC+).
Lines are drawn only from player-levels old enough for careers to play out.
"""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "analysis")
from tiers import wrc as mlb_wrc

LEVELS = {"A": "a", "A+": "aplus", "AA": "aa", "AAA": "aaa"}
CUTOFF = {"AAA": 2019, "AA": 2018, "A+": 2017, "A": 2016}   # last season used to draw lines
MIN_PA = 200

# ---------- 1. minor league wRC+ and age vs league ----------
frames = []
for lvl, f in LEVELS.items():
    d = pd.read_csv(f"data/history/{f}_hitting.csv.gz")
    d["level"] = lvl
    frames.append(d)
m = pd.concat(frames, ignore_index=True)
m = m[(m.season != 2020)]
for c in ["PA","AB","H","2B","3B","HR","BB","IBB","HBP","SF","R","SO","age"]:
    m[c] = pd.to_numeric(m[c], errors="coerce").fillna(0)
m = m[(m.pos != "P") & (m.PA > 0)]
# Prospects only: drop minor league seasons after a player already had a full MLB season
# (300+ PA) -- those are rehab stints, demotions and veterans, not development.
_mlb = pd.read_csv("data/history/mlb_hitting.csv.gz")
_mlb["PA"] = pd.to_numeric(_mlb.PA, errors="coerce").fillna(0)
_est = _mlb[_mlb.PA >= 300].groupby("player_id").season.min()
m = m[~(m.season > m.player_id.map(_est).fillna(9999))]
m["1B"] = m.H - m["2B"] - m["3B"] - m.HR
m["uBB"] = m.BB - m.IBB
m["raw"] = .69*m.uBB + .72*m.HBP + .89*m["1B"] + 1.27*m["2B"] + 1.62*m["3B"] + 2.10*m.HR
m["den"] = m.AB + m.uBB + m.SF + m.HBP
m["agePA"] = m.age * m.PA
key = ["level", "league", "season"]
L = m.groupby(key)[["raw","den","H","BB","HBP","AB","SF","R","PA","agePA"]].sum()
L["obp"] = (L.H + L.BB + L.HBP) / (L.AB + L.BB + L.HBP + L.SF)
L["scale"] = L.obp / (L.raw / L.den)
L["rpa"] = L.R / L.PA
L["lg_age"] = L.agePA / L.PA
m = m.join(L[["obp","scale","rpa","lg_age"]], on=key)
m["wOBA"] = m.raw / m.den.replace(0, np.nan) * m.scale
m["wRCplus"] = 100 * (((m.wOBA - m.obp) / 1.2) + m.rpa) / m.rpa
m["age_rel"] = m.age - m.lg_age

# ---------- one dot per player per level ----------
m["w_wrc"] = m.wRCplus * m.PA
m["w_age"] = m.age_rel * m.PA
m["w_K"] = m.SO
g = m.groupby(["player_id", "level"]).agg(
    name=("name", "last"), pos=("pos", lambda s: s.mode().iat[0]), PA=("PA", "sum"),
    first=("season", "min"), last=("season", "max"), team=("team", "last"),
    w_wrc=("w_wrc", "sum"), w_age=("w_age", "sum"), SO=("SO", "sum")).reset_index()
g["wRCplus"] = g.w_wrc / g.PA
g["age_rel"] = g.w_age / g.PA
g["K"] = 100 * g.SO / g.PA
g = g[g.PA >= MIN_PA].drop(columns=["w_wrc", "w_age"])

# ---------- 2. career outcome ----------
w = pd.read_csv("data/history/war_batting.csv.gz")
w = w[w.pitcher != "Y"]
for c in ["WAR", "PA"]: w[c] = pd.to_numeric(w[c], errors="coerce").fillna(0)
ws = w.groupby(["mlb_ID", "year_ID"], as_index=False)[["WAR", "PA"]].sum()
top = ws[ws.PA >= 300].sort_values("WAR", ascending=False).groupby("mlb_ID").head(3)
war3 = top.groupby("mlb_ID").WAR.sum() / 3
wq = mlb_wrc[mlb_wrc.PA >= 300].sort_values("wRCplus", ascending=False).groupby("player_id").head(3)
wrc3 = wq.groupby("player_id").wRCplus.mean()[wq.groupby("player_id").size() >= 3]
mlb_ids = set(pd.read_csv("data/history/mlb_hitting.csv.gz").player_id)

ORDER = ["Haze", "Just below regular", "Regular", "All-Star", "MVP"]
def tier_of(pid):
    if pid not in mlb_ids: return "Haze"
    a, b = war3.get(pid, 0.0), wrc3.get(pid, np.nan)
    ta = "MVP" if a >= 7.5 else "All-Star" if a >= 5 else "Regular" if a >= 3 else "Just below regular" if a >= 2 else "Haze"
    tb = ("Haze" if pd.isna(b) else "MVP" if b >= 165 else "All-Star" if b >= 140
          else "Regular" if b >= 115 else "Just below regular" if b >= 105 else "Haze")
    return ta if ORDER.index(ta) >= ORDER.index(tb) else tb
g["tier"] = g.player_id.map({p: tier_of(p) for p in g.player_id.unique()})
g["reached_mlb"] = g.player_id.isin(mlb_ids)
g["mature"] = g.apply(lambda r: r["last"] <= CUTOFF[r["level"]], axis=1)

# ---------- 3. lines ----------
def fit_line(d, q):
    """Straight line through the q-th percentile of wRC+ in each age step, weighted by count."""
    d = d.assign(step=d.age_rel.round().clip(-4, 3))
    pts = d.groupby("step").wRCplus.agg(lambda s: s.quantile(q)).rename("y").to_frame()
    pts["n"] = d.groupby("step").size()
    pts = pts[pts.n >= 5]
    b, a = np.polyfit(pts.index.values, pts.y.values, 1, w=np.sqrt(pts.n.values))
    return float(a), float(b)

out = {"levels": {}}
for lvl in LEVELS:
    d = g[(g.level == lvl) & g.mature]
    reg = d[d.tier.isin(["Regular", "All-Star", "MVP"])]
    star = d[d.tier.isin(["All-Star", "MVP"])]
    # One shared slope (from future regulars, the larger group) so the three lines run parallel;
    # each line's height comes from its own group.
    a_reg, b = fit_line(reg, 0.5)
    resid = lambda d: d.wRCplus - b * d.age_rel
    reg_line = (float(resid(reg).median()), b)      # middle of where future regulars sat
    star_line = (float(resid(star).median()), b)    # middle of where future All-Stars sat
    floor_line = (float(resid(reg).quantile(0.2)), b)  # 80% of future regulars sat above this
    def zone(r):
        x = r.age_rel
        if r.wRCplus >= star_line[0] + star_line[1]*x: return "Star zone"
        if r.wRCplus >= floor_line[0] + floor_line[1]*x: return "Channel"
        return "Below"
    d = d.assign(zone=d.apply(zone, axis=1))
    board = {}
    for z in ["Star zone", "Channel", "Below"]:
        s = d[d.zone == z]
        board[z] = dict(n=int(len(s)),
                        regular_plus=round(100*s.tier.isin(["Regular","All-Star","MVP"]).mean(), 1) if len(s) else 0,
                        allstar_plus=round(100*s.tier.isin(["All-Star","MVP"]).mean(), 1) if len(s) else 0,
                        reached=round(100*s.reached_mlb.mean(), 1) if len(s) else 0)
    dots = d[d.tier != "Haze"]
    haze = d[d.tier == "Haze"]
    out["levels"][lvl] = dict(
        cutoff=CUTOFF[lvl], n=int(len(d)),
        lines=dict(regular=reg_line, star=star_line, floor=floor_line),
        board=board,
        dots=[dict(name=r["name"], pos=r.pos, x=round(r.age_rel, 2), y=round(r.wRCplus), tier=r.tier,
                   yrs=f'{r["first"]}' if r["first"] == r["last"] else f'{r["first"]}-{r["last"]}', PA=int(r.PA))
              for _, r in dots.iterrows()],
        haze=[[round(x, 2), round(y)] for x, y in zip(haze.age_rel, haze.wRCplus)],
    )
    # how many eventual All-Stars+ sat below the floor here
    st = d[d.tier.isin(["All-Star", "MVP"])]
    out["levels"][lvl]["stars_below_floor"] = int((st.zone == "Below").sum())
    out["levels"][lvl]["stars_total"] = int(len(st))

json.dump(out, open("analysis/milb_lines.json", "w"))
if __name__ == "__main__":
    for lvl, v in out["levels"].items():
        r, s, f = v["lines"]["regular"], v["lines"]["star"], v["lines"]["floor"]
        print(f"\n{lvl} (through {v['cutoff']}, {v['n']} player-levels)")
        for x in (-3, -2, -1, 0, 1):
            print(f"  {x:+d} yrs: floor {f[0]+f[1]*x:5.0f}  regular {r[0]+r[1]*x:5.0f}  star {s[0]+s[1]*x:5.0f}")
        for z, b in v["board"].items():
            print(f"  {z:10s} n={b['n']:5d}  reached MLB {b['reached']:5.1f}%  regular+ {b['regular_plus']:5.1f}%  All-Star+ {b['allstar_plus']:5.1f}%")
        print(f"  All-Stars+ below the floor: {v['stars_below_floor']} of {v['stars_total']}")
