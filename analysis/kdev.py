"""K development: do young high-strikeout hitters cut their strikeouts, and does it matter?

Group: MLB hitters whose FIRST 30%+ strikeout season (350+ AB) came at age 25 or younger,
1980-2022 (three follow-up seasons available). Year zero = that season.
Follow-up = next three seasons combined. Fewer than 200 PA in them = washed out.
Luck baseline: same thing for hitters aged 28-31 in their 30%+ season, who are past development,
so their change is mostly regression to the mean (plus a little aging).
"""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "analysis")
from tiers import career, ORDER

TARGET = 695657  # Colson Montgomery

h = pd.read_csv("data/history/mlb_hitting.csv.gz")
for c in ["PA", "AB", "SO"]:
    h[c] = pd.to_numeric(h[c], errors="coerce").fillna(0)
h["age"] = pd.to_numeric(h.age, errors="coerce")
h["Kp"] = h.SO / h.PA.replace(0, np.nan)


def follow(pid, y0):
    f = h[(h.player_id == pid) & h.season.between(y0 + 1, y0 + 3)]
    pa, so = f.PA.sum(), f.SO.sum()
    return int(pa), (so / pa if pa else np.nan)


def bucket(row):
    if row.f_pa < 200: return "Washed out"
    d = row.change
    if d <= -5: return "Cut it a lot"
    if d <= -2: return "Cut it some"
    if d < 2: return "About the same"
    return "Got worse"


BUCKETS = ["Cut it a lot", "Cut it some", "About the same", "Got worse", "Washed out"]
_tier_cache = {}
def tier_of(pid):
    if pid not in _tier_cache:
        _tier_cache[pid] = career(pid)
    return _tier_cache[pid]


def build(k_cut=0.30, max_age=25, min_age=None, first_only=True, last=2022):
    q = h[(h.season.between(1980, last)) & (h.AB >= 350) & (h.Kp >= k_cut) & (h.player_id != TARGET)]
    if first_only:
        allq = h[(h.season >= 1980) & (h.AB >= 350) & (h.Kp >= k_cut)]
        first = allq.sort_values("season").drop_duplicates("player_id")
        q = first[first.season <= last]
    q = q[q.age <= max_age] if min_age is None else q[q.age.between(min_age, max_age)]
    q = q[q.player_id != TARGET].copy()
    fo = [follow(p, y) for p, y in zip(q.player_id, q.season)]
    q["f_pa"] = [a for a, _ in fo]
    q["f_K"] = [b for _, b in fo]
    q["change"] = (q.f_K - q.Kp) * 100
    q["bucket"] = q.apply(bucket, axis=1)
    return q


def outcomes(q):
    rows = []
    for b in BUCKETS:
        s = q[q.bucket == b]
        if not len(s):
            rows.append(dict(bucket=b, n=0)); continue
        tiers = [tier_of(p)["tier"] for p in s.player_id]
        idx = [ORDER.index(t) for t in tiers]
        rows.append(dict(bucket=b, n=len(s),
                         regular_plus=round(100 * np.mean([i >= 2 for i in idx]), 1),
                         allstar_plus=round(100 * np.mean([i >= 3 for i in idx]), 1),
                         below_repl=round(100 * np.mean([i == 0 for i in idx]), 1)))
    return rows


if __name__ == "__main__":
    out = {}
    g = build()
    vet = build(min_age=28, max_age=31, first_only=False)
    vet = vet[vet.f_pa >= 200]
    base = float(vet.change.median())
    stayed = g[g.f_pa >= 200]
    print(f"GROUP: {len(g)} players (first 30%+ K season at 25 or younger, 1980-2022)")
    print(f"  stayed in the majors (200+ PA next 3 yrs): {len(stayed)}")
    print(f"  median change, young group: {stayed.change.median():+.1f} pts   (mean {stayed.change.mean():+.1f})")
    print(f"  LUCK BASELINE, ages 28-31 with 30%+ K: n={len(vet)}, median change {base:+.1f} pts")
    beat = stayed[stayed.change <= base - 3]
    print(f"  young guys who beat the baseline by 3+ pts: {len(beat)} of {len(stayed)} ({100*len(beat)/len(stayed):.0f}%)")
    print()
    print(pd.DataFrame(outcomes(g)).to_string(index=False))

    # who cut it a lot
    g["tier"] = [tier_of(p)["tier"] for p in g.player_id]
    g["career_war"] = [tier_of(p)["career_war"] for p in g.player_id]
    lot = g[g.bucket == "Cut it a lot"].sort_values("change")
    print("\nCUT IT A LOT:")
    print(lot[["name", "season", "age", "Kp", "f_K", "change", "tier", "career_war"]].round(3).to_string(index=False))

    # sensitivity
    print("\nSENSITIVITY (share of those who stayed who cut 5+ pts / regular+ rate in that bucket):")
    for kc, ma in [(0.30, 25), (0.28, 25), (0.30, 26), (0.28, 26), (0.30, 24)]:
        s = build(kc, ma); st = s[s.f_pa >= 200]
        o = {r["bucket"]: r for r in outcomes(s)}
        print(f"  K>={kc:.0%} age<={ma}: n={len(s)}, stayed {len(st)}, cut 5+: {(st.change<=-5).mean()*100:.0f}%, "
              f"regular+ if cut a lot {o['Cut it a lot'].get('regular_plus')}%, if same {o['About the same'].get('regular_plus')}%, "
              f"washed out {(s.bucket=='Washed out').mean()*100:.0f}%")

    # Colson
    me = h[(h.player_id == TARGET)].sort_values("season")
    print("\nCOLSON:", me[["season", "age", "PA", "Kp"]].round(3).to_string(index=False))

    out["group"] = g[["player_id", "name", "season", "age", "PA", "Kp", "f_pa", "f_K", "change", "bucket", "tier", "career_war"]] \
        .round(4).to_dict("records")
    out["baseline_change"] = base
    out["buckets"] = outcomes(g)
    json.dump(out, open("analysis/kdev.json", "w"), default=float)
