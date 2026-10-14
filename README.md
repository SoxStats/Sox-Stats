# Sox Stats

Chicago White Sox stats page: season, last 30 and last 10 games, updated every morning from the MLB Stats API.
Live at https://soxstats.github.io/Sox-Stats/

## What's in here

- `docs/` — the public page. `docs/data/sox.json` is rebuilt every morning by `scripts/build.py`.
- `data/history/` — season stat lines for every player, rebuilt on the 1st of each month by `scripts/history.py`.
  - MLB: 1876 to the latest season. Minor leagues (AAA, AA, A+, A, A-, Rk): 2005 to the latest season.
  - One row per player, per season, per level, with the player's age that season.
  - Join seasons across levels with `player_id` (the MLB ID), never by name.
  - No minor league games were played in 2020; short-season A (A-) ended after 2019.
  - Before 2022, MLB hitting includes pitchers who batted.
