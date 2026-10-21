"""Fill the data line (const D=...) in docs/articles/how-rare-is-a-harold/index.html
from analysis/harold_study.csv and .json. Run harold_study.py first."""
import json, re
import pandas as pd

PAGE = "docs/articles/how-rare-is-a-harold/index.html"
m = pd.read_csv("analysis/harold_study.csv")
r = json.load(open("analysis/harold_study.json"))

TIERS = [  # name, range, example, plain-English line
    ("MVP candidate", "7.5+ WAR", "Albert Pujols", "Best three years averaged MVP-level play."),
    ("All-Star", "5 to 7.5", "Derek Jeter", "Three seasons at an All-Star level."),
    ("Solid regular", "3 to 5", "Paul Konerko", "A good everyday player for years."),
    ("Borderline starter", "2 to 3", "Nick Castellanos", "An average everyday player."),
    ("Role player", "1 to 2", "Neifi Pérez", "Platoon, utility or part-time starter."),
    ("Fringe", "0 to 1", "Jeff Mathis", "Bench filler who hung around."),
    ("Below replacement", "0 or less", "Yuniesky Betancourt", "Cost his team wins over his career."),
]
for name, _, ex, _ in TIERS:
    got = m[m.name_common == ex].tier.tolist()
    assert got == [name], f"{ex} is {got}, not {name}"

stars = ["MVP candidate", "All-Star"]
regs = stars + ["Solid regular"]
mm = r["milb_since_2005"]
route = []
for label, key in [("Drafted (US, CAN, PR)", "Drafted pool (US/CAN/PR)"), ("International", "International signing")]:
    g = m[m.route == key]
    route.append([label, len(g), int((g.tier == "MVP candidate").sum()), int(g.tier.isin(stars).sum()),
                  int(g.tier.isin(regs).sum()), int(g.harold.sum())])

peaks = m[~m.harold & m.tier.isin(stars)].sort_values("best3", ascending=False)
neg = r["neg_career_sidebar"]
D = dict(
    total=len(m), harolds=int(m.harold.sum()), harold=r["harold_war"],
    below=int((m.tier == "Below replacement").sum()),
    tiers=[[n, rg, int((m.tier == n).sum()), ex, line] for n, rg, ex, line in TIERS],
    funnel=[["Reached High-A", mm["reached_high_a"]], ["Made the majors", mm["made_mlb"]],
            ["Got 500 at-bats", mm["got_500_ab"]], ["Became a Harold", mm["harolds"]]],
    players=[[p.name_common, int(p.debut), int(p.AB), float(p.career_war), float(p.best3), p.tier,
              int(bool(p.harold)), int(bool(p.active))]
             for p in m.sort_values("career_war", ascending=False).itertuples()],
    chase=[[c["name_common"], c["career_war"], int(c["age_now"])] for c in r["chasing"] if c["career_war"] >= 30],
    peaks_total=len(peaks),
    peaks=[[p.name_common, float(p.best3), float(p.career_war), int(bool(p.active))] for p in peaks.head(12).itertuples()],
    route=route,
    neg=dict(count=neg["count"], good_fielders=neg["good_fielders"],
             list=[[p["name_common"], int(p["AB"]), p["career_war"]] for p in neg["most_at_bats"][:8]]),
)
html = open(PAGE).read()
data = "const D=" + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";"
html = re.sub(r"^const D=.*;$", lambda _: data,
              html, count=1, flags=re.M)
open(PAGE, "w").write(html)
print("players", D["total"], "harolds", D["harolds"], "tiers", [t[2] for t in D["tiers"]], "peaks", D["peaks_total"])
