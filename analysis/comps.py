"""Colson Montgomery comps: who looked like his 2026 season, and how did they turn out?"""
import pandas as pd, numpy as np, json

TARGET = 695657          # Colson Montgomery
TARGET_SEASON = 2026
K_BAND = 0.12            # +/- on league-relative K rate (about +/- 2.7 K% points today)
AGE = (22, 26)
MIN_AB = 350
LAST_COMP_SEASON = 2018  # comps need time for their careers to play out
FIRST_COMP_SEASON = 1920
N = 150

h = pd.read_csv("data/history/mlb_hitting.csv.gz")
num = ["PA","AB","H","2B","3B","HR","BB","SO","HBP","SF","R","IBB"]
for c in num: h[c] = pd.to_numeric(h[c], errors="coerce").fillna(0)
h["age"] = pd.to_numeric(h["age"], errors="coerce")

lg = h[h.pos != "P"].groupby("season")[["PA","AB","H","2B","3B","HR","BB","SO","HBP"]].sum()
lg["K"] = lg.SO / lg.PA
lg["BBr"] = lg.BB / lg.PA
lg["ISO"] = (lg["2B"] + 2*lg["3B"] + 3*lg.HR) / lg.AB

h = h.join(lg[["K","BBr","ISO"]].add_prefix("lg_"), on="season")
h["Kp"] = h.SO / h.PA
h["BBp"] = h.BB / h.PA
h["ISOv"] = (h["2B"] + 2*h["3B"] + 3*h.HR) / h.AB
h["relK"] = h.Kp / h.lg_K
h["relBB"] = h.BBp / h.lg_BBr
h["relISO"] = h.ISOv / h.lg_ISO

me = h[(h.player_id == TARGET) & (h.season == TARGET_SEASON)].iloc[0]

pool = h[(h.season.between(FIRST_COMP_SEASON, LAST_COMP_SEASON)) & (h.AB >= MIN_AB)
         & (h.age.between(*AGE)) & ((h.relK - me.relK).abs() <= K_BAND)
         & (h.player_id != TARGET)].copy()

# distance on power and walks, scaled by how spread out each is in the pool
sd = pool[["relISO","relBB"]].std()
pool["dist"] = np.sqrt(((pool.relISO - me.relISO)/sd.relISO)**2 + ((pool.relBB - me.relBB)/sd.relBB)**2)
pool = pool.sort_values("dist").drop_duplicates("player_id")   # each player once, his closest season
comps = pool.head(N).reset_index(drop=True)
comps["rank"] = comps.index + 1

if __name__ == "__main__":
    print("Colson 2026:", dict(K=round(me.Kp,3), lgK=round(me.lg_K,3), relK=round(me.relK,2),
          relISO=round(me.relISO,2), relBB=round(me.relBB,2), age=me.age))
    print("pool (unique players):", len(pool))
    print(comps[["rank","name","season","age","team","AB","HR","Kp","relK","relISO","relBB","dist"]].head(25).round(2).to_string(index=False))
    print("...worst kept dist", round(comps.dist.max(),2))
