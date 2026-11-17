"""Fill the data line (const D=...) in docs/articles/see-it-coming/index.html from analysis/aa_study.json.
Run analysis/aa_study.py [PLAYER_ID] first."""
import json, re

PAGE = "docs/articles/see-it-coming/index.html"
r = json.load(open("analysis/aa_study.json"))
A = {x["group"]: x for x in r["by_age"]}
young3, avg = A["3+ years young"], A["About league age"]
K = {x["band"]: x for x in r["kguess"]}
hiK, loK, midK = (K["Strikes out a lot (20%+ above league)"], K["Rarely strikes out (15%+ below league)"],
                  K["About league average"])
sep = {x["stat"]: x for x in r["separators"]}
ks = sep["K_rel"]
best = r["separators"][0]
one_in = lambda pct: round(100 / pct)
rc = r["race"]

short = (f"Partly. How young a hitter was for AA mattered more than anything: {round(young3['made'])}% of the hitters "
         f"3+ years young became solid regulars or better, compared with {avg['made']:.1f}% of the ones at league age. "
         f"After that it was the bat and the power. Strikeouts barely mattered.")
take1 = (f"Same level, very different odds. A hitter 3+ years young for AA made it about 1 in {one_in(young3['made'])} times. "
         f"A hitter at his league's average age made it about 1 in {one_in(avg['made'])}.")
take2 = (f"{best['label'].split(' (')[0]} and power separated them most. Strikeout rate was the weakest signal on the list, and it didn't "
         f"separate the stars at all: about {round(ks['Low']['star'])}% of each third became All-Stars. (Power and batting average landing on "
         f"the exact same numbers isn't a typo. Different hitters, same counts.)")
kintro = (f"Hitters 2+ years young with a 130+ wRC+ at AA, way above average, split by how often they struck out "
          f"compared with their league. {hiK['n'] + midK['n'] + loK['n']} hitters in all.")
take3 = (f"My guess was wrong. The young raking hitters who struck out a lot made it {round(hiK['made'])}% of the time, about the same as "
         f"the low-strikeout group ({round(loK['made'])}%). Yelich, Bryant, Tatis and Olson all struck out plenty at AA. "
         f"These are small groups, so call it a lean, not a law. And yes, that's Tyler Flowers on the bust list.")
take4 = (f"In the minors the next year, both groups hit about the same as before (wRC+ {rc['made']['now_wRC']} to {rc['made']['next_wRC']} "
         f"for the ones who made it, {rc['didnt']['now_wRC']} to {rc['didnt']['next_wRC']} for the rest). The real split: "
         f"{round(rc['made']['straight_up'])}% of the future regulars were already in the majors, compared with "
         f"{round(rc['didnt']['straight_up'])}% of everybody else. The teams saw something too.")
conclusion = [
    "You can see some of it coming. Age is the biggest tell. Being young for AA and holding your own is the strongest sign there is.",
    "After age, it's the bat: overall production and power. Strikeouts, the thing everybody (me included) worries about, were the weakest "
    "signal of all. That doesn't mean strikeouts don't matter in the majors. It means a young hitter who strikes out a lot at AA isn't "
    "doomed if he's doing damage when he connects.",
    f"And even the young hitters who raked at AA made it only about 1 in {one_in((hiK['made']*hiK['n'] + loK['made']*loK['n'] + midK['made']*midK['n']) / (hiK['n'] + loK['n'] + midK['n']))} times. The numbers narrow it down. They don't call it.",
]
method = [
    f"<b>Who's in it.</b> Every hitter's first season at AA with 200+ plate appearances, 2005 to 2018: {r['pool']:,} hitters. "
    "2005 is as far back as our minor league numbers go. Stopping at 2018 gives every career 8+ years to play out. "
    "Big leaguers on rehab or sent back down don't count.",
    "<b>How young.</b> His age that season minus the average age of his league, weighted by playing time.",
    "<b>Stats against his league.</b> Every stat is compared with his own league that year. Strikeouts are way up since 2005, "
    "so a 25% strikeout rate meant something different in 2008 than in 2018.",
    f"<b>Made it.</b> Solid regular or better: his best 3 big league seasons averaged 3+ WAR (Baseball-Reference), with 500+ "
    "at-bats. Star means All-Star level, 5+. Same tiers as <a href=\"../how-good-is-good/\">How good is good?</a>",
    "<b>Holding age steady.</b> In Chart 2, each stat is split into thirds within each age group, so a 20-year-old is only "
    "ranked against other hitters his age. Otherwise age would swamp everything else.",
    "<b>What's not in here.</b> Defense, position, injuries, draft spot, scouting reports. This is the bat only.",
]

p = r.get("player")
if p:
    last = p["name"].split(" ", 1)[1]
    band = K[p["k_band"]]
    ordn = lambda n: f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
    p["last"] = last
    p["html"] = (
        f'<span class="eyebrow">So where does {p["name"]} land?</span>'
        f"<ul><li>He was <b>{abs(p['age_rel'])} years young</b> for AA in {p['season']}, so he's in the best group on Chart 1.</li>"
        f"<li>His <b>wRC+ of {p['wRC']}</b> beat {p['pct']['wRCplus']}% of that group, and his <b>power</b> beat {p['pct']['ISO_rel']}%. "
        f"Those were the top two signals.</li>"
        f"<li>He struck out <b>{p['K']}%</b> of the time. That sounds like a lot, but AA strikes out a lot now. It's only "
        f"{p['K_rel'] - 100}% above his league, which puts him in the middle group on Chart 3: young hitters who raked made it "
        f"{round(band['made'])}% of the time there, and {round(band['star'])}% became stars.</li></ul>"
        f'<a href="../../prospects/caleb-bonemer/">See the 10 hitters most like him, and what they became →</a>')

D = dict(short=short, take1=take1, take2=take2, take3=take3, take4=take4, kintro=kintro, conclusion=conclusion,
         method=method, by_age=r["by_age"], separators=r["separators"], kguess=r["kguess"], race=r["race"], player=p)
html = open(PAGE).read()
data = "const D=" + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";"
html = re.sub(r"^const D=.*;$", lambda _: data, html, count=1, flags=re.M)
open(PAGE, "w").write(html)
for k in ("short", "take1", "take2", "take3", "take4"): print(k, "|", D[k])
