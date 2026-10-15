"""Statcast side of the K-development study (2015 on).
Young (26 and under) hitters with a 27%+ K season in 300+ PA, 2015-2023.
Does chase rate or whiff rate in that season tell us who cuts strikeouts over the next two years?"""
import json, numpy as np, pandas as pd
s = pd.read_csv("data/history/savant_batting.csv.gz")
m = pd.read_csv("data/history/mlb_hitting.csv.gz")[["player_id", "season", "age"]]
s = s.merge(m, on=["player_id", "season"], how="left")
lg = s[s.pa >= 300].groupby("season")[["k_percent", "chase", "whiff"]].median()
print("league medians (300+ PA):"); print(lg.round(1).tail(4).to_string())

def nxt(pid, y):
    f = s[(s.player_id == pid) & s.season.between(y + 1, y + 2)]
    pa = f.pa.sum()
    if pa < 300: return np.nan, np.nan, np.nan
    w = lambda c: (f[c] * f.pa).sum() / pa
    return w("k_percent"), w("chase"), w("whiff")

g = s[(s.pa >= 300) & (s.k_percent >= 27) & (s.age <= 26) & s.season.between(2015, 2023) & (s.player_id != 695657)].copy()
g = g.sort_values("season").drop_duplicates("player_id")
r = [nxt(p, y) for p, y in zip(g.player_id, g.season)]
g["k2"], g["chase2"], g["whiff2"] = zip(*r)
g = g.dropna(subset=["k2"])
g["dk"] = g.k2 - g.k_percent
print(f"\nyoung 27%+ K group with 2 follow-up years: n={len(g)}, median K change {g.dk.median():+.1f}")
print("correlation with K change:  chase", round(g.dk.corr(g.chase), 2), "  whiff", round(g.dk.corr(g.whiff), 2))
X = np.c_[np.ones(len(g)), g.k_percent, g.chase, g.whiff]
coef, *_ = np.linalg.lstsq(X, g.k2, rcond=None)
print("next-2-yr K = %.1f + %.2f*K + %.2f*chase + %.2f*whiff" % tuple(coef))
for lab, sub in [("chase below 28", g[g.chase < 28]), ("chase 28+", g[g.chase >= 28]),
                 ("whiff below 32", g[g.whiff < 32]), ("whiff 32+", g[g.whiff >= 32])]:
    print(f"  {lab:15s} n={len(sub):3d}  median K change {sub.dk.median():+.1f}  cut 3+ pts: {(sub.dk <= -3).mean()*100:.0f}%")
cut = g[g.dk <= -3]
print(f"\nguys who cut 3+ pts (n={len(cut)}): median change in chase {(cut.chase2-cut.chase).median():+.1f}, whiff {(cut.whiff2-cut.whiff).median():+.1f}")
print(f"everyone else: chase {(g[g.dk>-3].chase2-g[g.dk>-3].chase).median():+.1f}, whiff {(g[g.dk>-3].whiff2-g[g.dk>-3].whiff).median():+.1f}")
c = s[s.player_id == 695657]
pred = coef[0] + coef[1]*35.6 + coef[2]*32.4 + coef[3]*37.4
print(f"\nColson 2026: K 35.6, chase 32.4, whiff 37.4 -> model says next two years about {pred:.1f}%")
pct = lambda col, v: (s[(s.pa >= 300) & (s.season == 2026)][col] < v).mean() * 100
print(f"  Colson 2026 percentile among 300+ PA hitters: chase {pct('chase',32.4):.0f}th, whiff {pct('whiff',37.4):.0f}th")
print(g.sort_values("whiff", ascending=False)[["name","season","age","k_percent","chase","whiff","k2","dk"]].head(15).round(1).to_string(index=False))
json.dump(dict(n=len(g), coef=list(coef), colson_pred=pred), open("analysis/kdev_savant.json", "w"))
