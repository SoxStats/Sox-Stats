import sys; sys.path.insert(0, "analysis")
import pandas as pd, numpy as np, json
from comps_k30 import comps, me
from tiers import career, ORDER

w = pd.read_csv("data/history/war_batting.csv.gz")
w = w[w.pitcher != "Y"]
for c in ["WAR","WAR_def","runs_field","runs_position","PA"]: w[c] = pd.to_numeric(w[c], errors="coerce").fillna(0)
ws = w.groupby(["mlb_ID","year_ID"], as_index=False)[["WAR","WAR_def","runs_field","runs_position","PA"]].sum()
def season_def(pid, yr):
    r = ws[(ws.mlb_ID == pid) & (ws.year_ID == yr)]
    return (None, None, None) if r.empty else (round(float(r.runs_field.iloc[0]),1), round(float(r.WAR_def.iloc[0]),1), round(float(r.WAR.iloc[0]),1))

rows = []
for _, c in comps.iterrows():
    r = career(c.player_id)
    fld, wdef, swar = season_def(c.player_id, c.season)
    rows.append(dict(rank=int(c["rank"]), name=c["name"], season=int(c.season), age=int(c.age), pos=c.pos,
                     team=c.team, AB=int(c.AB), HR=int(c.HR), K=round(c.Kp*100,1), too_early=bool(c.too_early),
                     times30=int(c.times_over_30), field=fld, war_def=wdef, season_war=swar, **r))
df = pd.DataFrame(rows)
me_fld, me_def, me_war = season_def(me.player_id, 2026)
print("Colson 2026: runs_field", me_fld, "WAR_def", me_def, "WAR", me_war, "pos", me.pos)
df.to_csv("analysis/k30_comps.csv", index=False)
json.dump({"colson": dict(field=me_fld, war_def=me_def, war=me_war, K=round(me.Kp*100,1), age=int(me.age)),
           "rows": json.loads(df.to_json(orient="records"))}, open("analysis/k30_comps.json","w"))

c = df[~df.too_early]
def show(d, label):
    t = d.tier.value_counts().reindex(ORDER[::-1], fill_value=0); p = d.peak.value_counts().reindex(ORDER[::-1], fill_value=0)
    print(f"\n{label} n={len(d)}"); print(pd.DataFrame({"tier":t,"%":(100*t/len(d)).round(0),"peak":p,"peak%":(100*p/len(d)).round(0)}).to_string())
show(c, "Counted (first 30% season 1980-2021)")
show(c[c.age <= 26], "Counted, age 26 or younger")
show(c[c.age >= 27], "Counted, age 27+")
print("\nAll-Star+ settled:", c[c.tier.isin(["All-Star","MVP candidate"])][["name","season","age","pos","K","war3","wrc3","tier","peak","field"]].to_string(index=False))
print("\nfield runs, counted: median", c.field.median(), " share with field>=5:", round((c.field>=5).mean()*100))
print("Colson-like glove (field>=5) outcomes:"); print(c[c.field>=5][["name","season","age","pos","K","field","war3","tier","peak"]].to_string(index=False))
print("\nToo early:", ", ".join(df[df.too_early].name.head(42)))
