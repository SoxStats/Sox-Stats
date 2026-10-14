import sys, json; sys.path.insert(0, "analysis")
import pandas as pd
import os, importlib
_m = importlib.import_module(os.environ.get("COMPS", "comps"))
comps, me, pool = _m.comps, _m.me, _m.pool
from tiers import career, ORDER

rows = []
for _, c in comps.iterrows():
    r = career(c.player_id)
    rows.append(dict(rank=int(c["rank"]), name=c["name"], season=int(c.season), age=int(c.age),
                     team=c.team, AB=int(c.AB), HR=int(c.HR), K=round(c.Kp*100,1),
                     relK=round(c.relK,2), relISO=round(c.relISO,2), relBB=round(c.relBB,2),
                     dist=round(c.dist,3), **r))
df = pd.DataFrame(rows)
df.to_csv(os.environ.get("OUT", "analysis/colson_comps.csv"), index=False)

def summary(d, label):
    t = d.tier.value_counts().reindex(ORDER[::-1], fill_value=0)
    pk = d.peak.value_counts().reindex(ORDER[::-1], fill_value=0)
    print(f"\n{label} (n={len(d)})")
    print(pd.DataFrame({"tier": t, "tier%": (100*t/len(d)).round(0), "peak": pk, "peak%": (100*pk/len(d)).round(0)}).to_string())
    print("peak one tier above tier:", (d.jump == 1).sum(), " two+ tiers:", (d.jump >= 2).sum())

summary(df, "All 150")
summary(df.head(25), "Closest 25")
print("\nTwo-tier jumps:", df[df.jump >= 2][["name","season","tier","peak","war3","peak_war","wrc3","peak_wrc"]].to_string(index=False))
print("\nTop careers:", df.sort_values("career_war", ascending=False).head(12)[["rank","name","season","career_war","tier","peak"]].to_string(index=False))
