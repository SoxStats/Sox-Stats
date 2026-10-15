"""Minor league side of the K-development study (2005 on).
1) AAA-to-MLB strikeout translation: AAA K% (all AAA time before his first 300-PA MLB season, 200+ PA)
   vs K% in that first 300-PA MLB season.
2) For the young high-K group: their AA and AAA strikeout rates on the way up.
"""
import json, numpy as np, pandas as pd

def load(f):
    d = pd.read_csv(f"data/history/{f}_hitting.csv.gz")
    for c in ["PA", "SO"]: d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0)
    return d[d.pos != "P"]
mlb, aaa, aa = load("mlb"), load("aaa"), load("aa")
first300 = mlb[mlb.PA >= 300].sort_values("season").drop_duplicates("player_id").set_index("player_id")

def minors(d, pid, before):
    s = d[(d.player_id == pid) & (d.season < before)] if before else d[d.player_id == pid]
    return int(s.PA.sum()), (s.SO.sum() / s.PA.sum() if s.PA.sum() else np.nan)

rows = []
for pid, r in first300.iterrows():
    if r.season < 2007: continue
    pa, k = minors(aaa, pid, r.season)
    if pa >= 200 and r.season != 2020:
        rows.append(dict(pid=pid, name=r["name"], season=r.season, aaa_pa=pa, aaa_k=k, mlb_k=r.SO / r.PA))
t = pd.DataFrame(rows)
t["diff"] = (t.mlb_k - t.aaa_k) * 100
b, a = np.polyfit(t.aaa_k, t.mlb_k, 1)
print(f"AAA -> MLB translation: n={len(t)}  median jump {t['diff'].median():+.1f} pts, mean {t['diff'].mean():+.1f}")
print(f"  fit: MLB K = {a:.3f} + {b:.2f} x AAA K")
hi = t[t.aaa_k >= 0.27]
print(f"  AAA K 27%+: n={len(hi)}, median MLB K {hi.mlb_k.median():.3f}, median jump {hi['diff'].median():+.1f}")
for x in (0.20, 0.25, 0.28, 0.30, 0.32):
    print(f"  AAA {x:.0%} -> about {a + b*x:.1%} in MLB")

# Colson
c_pa, c_k = minors(aaa, 695657, None)
print(f"\nColson AAA: {c_pa} PA, {c_k:.1%} K -> fit says {a + b*c_k:.1%}; actual 2026 35.6%")

# the young group on the way up
g = pd.DataFrame(json.load(open("analysis/kdev.json"))["group"])
g = g[g.season >= 2007]
out = []
for _, r in g.iterrows():
    p1, k1 = minors(aa, r.player_id, r.season + 1)
    p2, k2 = minors(aaa, r.player_id, r.season + 1)
    out.append(dict(name=r["name"], y0=r.season, AA=round(k1*100,1) if p1 >= 100 else None, AA_pa=p1,
                    AAA=round(k2*100,1) if p2 >= 100 else None, AAA_pa=p2, MLB0=round(r.Kp*100,1),
                    next3=round(r.f_K*100,1), bucket=r.bucket, tier=r.tier))
print()
print(pd.DataFrame(out).sort_values("next3").to_string(index=False))
json.dump(dict(translation=dict(n=len(t), a=a, b=b, median_jump=float(t["diff"].median())),
               colson=dict(aaa_pa=c_pa, aaa_k=c_k), group=out), open("analysis/kdev_milb.json", "w"), default=float)
