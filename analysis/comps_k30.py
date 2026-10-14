"""Colson comps, version 3: everyone who struck out 30%+ in a 350-AB season, 1980-2025, first doing it by age 32.
Any age. Each player counted once, at his FIRST 30%+ season.
Players whose first 30%+ season was 2022 or later are 'too early to tell'."""
import pandas as pd
from comps import h, me

TOO_EARLY_FROM = 2022
q = h[(h.season.between(1980, 2025)) & (h.AB >= 350) & (h.Kp >= 0.30)
      & (h.player_id != me.player_id)].copy()
MAX_AGE = 32   # first 30% season after 32 is decline, not development
pool = q.sort_values("season").drop_duplicates("player_id")     # first 30%+ season
pool = pool[pool.age <= MAX_AGE]
pool["too_early"] = pool.season >= TOO_EARLY_FROM
pool["times_over_30"] = pool.player_id.map(q.player_id.value_counts())
comps = pool.sort_values("Kp", ascending=False).reset_index(drop=True)
comps["rank"] = comps.index + 1
comps["dist"] = 0.0

if __name__ == "__main__":
    print("players:", len(comps), " too early:", comps.too_early.sum(), " counted:", (~comps.too_early).sum())
    print(comps.season.value_counts(bins=[1979,1989,1999,2009,2014,2018,2021,2025]).sort_index())
    print(comps.age.describe().round(1))
