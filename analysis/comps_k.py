"""Colson comps, version 2: the 150 highest raw strikeout rates.
350+ AB, age 22-26, seasons 1980-2018, one season per player (his highest-K one)."""
import pandas as pd
from comps import h, me      # same cleaned data and Colson's 2026 line

N = 150
pool = h[(h.season.between(1980, 2018)) & (h.AB >= 350) & (h.age.between(22, 26))
         & (h.player_id != me.player_id)].copy()
pool = pool.sort_values("Kp", ascending=False).drop_duplicates("player_id")
comps = pool.head(N).reset_index(drop=True)
comps["rank"] = comps.index + 1
comps["dist"] = 0.0

if __name__ == "__main__":
    print("K range:", round(comps.Kp.min()*100,1), "to", round(comps.Kp.max()*100,1))
    print(comps.season.value_counts(bins=[1979,1989,1999,2009,2018]).sort_index())
    print(comps[["rank","name","season","age","AB","HR","Kp"]].head(10).round(3).to_string(index=False))
