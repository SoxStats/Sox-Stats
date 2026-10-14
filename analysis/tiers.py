"""Career tiers: best-3-season WAR and wRC+ averages, plus peak season."""
import pandas as pd, numpy as np

MIN_PA = 300
WAR_CUTS = [(7.5, "MVP candidate"), (5, "All-Star"), (3, "Solid regular"), (0, "Just a guy")]
WRC_CUTS = [(165, "MVP candidate"), (140, "All-Star"), (115, "Solid regular"), (90, "Just a guy")]
ORDER = ["Below replacement", "Just a guy", "Solid regular", "All-Star", "MVP candidate"]

def tier(v, cuts):
    if v is None or pd.isna(v): return "Below replacement"
    for c, name in cuts:
        if v >= c: return name
    return "Below replacement"

def better(a, b): return a if ORDER.index(a) >= ORDER.index(b) else b

# --- our wRC+ (league-adjusted, not park-adjusted), every MLB season ---
h = pd.read_csv("data/history/mlb_hitting.csv.gz")
for c in ["PA","AB","H","2B","3B","HR","BB","IBB","HBP","SF","R"]:
    h[c] = pd.to_numeric(h[c], errors="coerce").fillna(0)
h["1B"] = h.H - h["2B"] - h["3B"] - h.HR
h["uBB"] = h.BB - h.IBB
h["raw"] = .69*h.uBB + .72*h.HBP + .89*h["1B"] + 1.27*h["2B"] + 1.62*h["3B"] + 2.10*h.HR
h["den"] = h.AB + h.uBB + h.SF + h.HBP
L = h.groupby("season")[["raw","den","H","BB","HBP","AB","SF","R","PA"]].sum()
L["obp"] = (L.H + L.BB + L.HBP) / (L.AB + L.BB + L.HBP + L.SF)
L["scale"] = L.obp / (L.raw / L.den)          # sets league wOBA = league OBP
L["rpa"] = L.R / L.PA
h = h.join(L[["scale","obp","rpa"]], on="season")
h["wOBA"] = h.raw / h.den.replace(0, np.nan) * h.scale
h["wRCplus"] = 100 * (((h.wOBA - h.obp) / 1.2) + h.rpa) / h.rpa
wrc = h[["player_id","season","PA","wRCplus"]]

# --- Baseball-Reference WAR by player-season (stints combined) ---
w = pd.read_csv("data/history/war_batting.csv.gz")
w = w[w.pitcher != "Y"]
w["WAR"] = pd.to_numeric(w.WAR, errors="coerce").fillna(0)
w["PA"] = pd.to_numeric(w.PA, errors="coerce").fillna(0)
war = w.groupby(["mlb_ID","year_ID"], as_index=False).agg(WAR=("WAR","sum"), PA=("PA","sum"))
war = war.rename(columns={"mlb_ID":"player_id","year_ID":"season"})

def career(pid):
    sw = war[war.player_id == pid]
    q = sw[sw.PA >= MIN_PA].sort_values("WAR", ascending=False)
    top = list(q.WAR.head(3)) + [0.0]*(3 - min(3, len(q)))   # missing seasons count as 0
    war3 = round(float(np.mean(top)), 2)
    peak_war = round(float(q.WAR.max()), 1) if len(q) else None
    sr = wrc[(wrc.player_id == pid) & (wrc.PA >= MIN_PA)].sort_values("wRCplus", ascending=False)
    wrc3 = round(float(sr.wRCplus.head(3).mean())) if len(sr) >= 3 else None
    peak_wrc = round(float(sr.wRCplus.max())) if len(sr) else None
    t = better(tier(war3, WAR_CUTS), tier(wrc3, WRC_CUTS))
    p = better(tier(peak_war, WAR_CUTS), tier(peak_wrc, WRC_CUTS))
    p = better(p, t)
    return dict(career_war=round(float(sw.WAR.sum()),1), qual_seasons=len(q),
                war3=round(war3,2), wrc3=None if wrc3 is None else round(wrc3),
                peak_war=None if peak_war is None else round(peak_war,1),
                peak_wrc=None if peak_wrc is None else round(peak_wrc),
                tier=t, peak=p, jump=ORDER.index(p) - ORDER.index(t))
