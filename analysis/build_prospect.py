"""Build a prospect's "company he keeps" page from templates/prospect.html.

Run analysis/company.py PLAYER_ID first, then:
  python3 analysis/build_prospect.py PLAYER_ID SLUG ["intro paragraph html"]
Writes docs/prospects/SLUG/index.html. The intro is kept from the existing page if not given.
"""
import json, os, re, sys

pid, slug = sys.argv[1], sys.argv[2]
r = json.load(open(f"analysis/company/{pid}.json"))
page = f"docs/prospects/{slug}/index.html"
intro = sys.argv[3] if len(sys.argv) > 3 else None
if intro is None and os.path.exists(page):
    m = re.search(r'<div class="prose" id="intro">(.*?)</div>', open(page).read(), flags=re.S)
    intro = m.group(1) if m else ""
intro = intro or ""

STAR, REG = ["MVP candidate", "All-Star"], ["Solid regular"]
ROLE, MISS = ["Borderline starter", "Role player"], ["Fringe", "Below replacement", "Cup of coffee", "Never made it"]
def groups(t): return [sum(t[k] for k in g) for g in (STAR, REG, ROLE, MISS)]
def words(n, one, many): return f"{n} {one if n == 1 else many}"

NUM = {2: "Two", 3: "Three", 4: "Four", 5: "Five"}
last = r["name"].split(" ", 1)[1]
A = r["stops"][-1]
n = len(r["comps"])
s, g, ro, mi = groups(r["tally"])
harolds = [c["name"].split(" ", 1)[1] for c in r["comps"] if c["harold"]]
bits = [words(s, "became a star", "became stars")] if s else []
if g: bits.append(words(g, "a solid regular", "solid regulars"))
if ro: bits.append(f"{ro} had a role")
if mi: bits.append(f"{mi} didn't pan out")
short = f"Of the {n} hitters most like him through age {A['age']}, " + ", ".join(bits[:-1]) + (" and " if len(bits) > 1 else "") + bits[-1] + "."
if harolds:
    short += " " + (f"{harolds[0]} is already a Harold." if len(harolds) == 1 else
                    f"{NUM.get(len(harolds), len(harolds))} are already Harolds ({', '.join(harolds)}).")

names = lambda tiers: [c["name"].split(" ", 1)[1] for c in r["comps"] if c["tier"] in tiers]
take10 = (f"Became regulars or better: {', '.join(names(STAR + REG))}. Didn't: {', '.join(names(ROLE + MISS))}. "
          f"Same numbers at the same age, very different careers.")
ws, wg, wro, wmi = groups(r["wide"]["tally"])
W = r["wide"]["n"]
junk = r["wide"]["tally"]["Cup of coffee"] + r["wide"]["tally"]["Never made it"]
takewide = (f"Out of {W}: {ws} stars, {wg} solid regulars, {wro} who had a role and {wmi} who didn't pan out, "
            f"including {junk} who got a cup of coffee or never made it at all. "
            f"About 1 in {round(W / ws) if ws else '?'} became a star.")

pos = "/".join(dict.fromkeys(st["pos"] for st in reversed(r["stops"])))
meta = f"{pos} · Age {A['age']} · Finished {A['season']} at {A['level']} {A['team']} · Built from his minor league numbers through {A['season']}"
P = r["pool"]
method = [
    "<b>The pool.</b> Every minor league hitter since 2005 (as far back as our minor league numbers go) at Single-A, High-A, AA and AAA. One stop is one player at one level in one season, with 200+ plate appearances. Big leaguers on rehab or sent back down don't count.",
    f"<b>Who can be a comp.</b> He had to play {A['level']} within a year of the same age ({A['age']}). That left {P['candidates']} hitters. Age matters most, so every year of age gap costs a comp heavily.",
    "<b>What gets compared.</b> Overall bat (wRC+), strikeout rate, walk rate, power and steals. Each one is measured against the player's own league that season, so a 25% strikeout rate in 2006 and in 2026 aren't treated as the same thing.",
    "<b>His whole road, not one stop.</b> Each of his stops is compared, weighted by playing time, with higher levels counting a bit more. A comp who skipped one of his earlier levels, or had under 200 plate appearances there, gets charged a penalty for it.",
    f"<b>Who gets a grade.</b> Only comps who played {A['level']} in {P['cutoff']} or earlier, so they've had 8+ years to show what they are ({P['scored']} hitters). Newer ones are listed under Too soon to call.",
    f"<b>The grades.</b> Same tiers as <a href=\"../../articles/how-good-is-good/\">How good is good?</a>: the average of a player's best 3 seasons by Baseball-Reference WAR, for anyone with 500+ big league at-bats. Under 500 at-bats is a cup of coffee. A Harold is {r['harold']} career WAR.",
    "<b>What's not in here.</b> Defense, position, injuries, scouting. This is the bat only. A first baseman and a shortstop with the same line are the same comp here, and they aren't the same player.",
]

keep = ["key", "level", "season", "age", "team", "PA", "AVG", "OBP", "SLG", "HR", "SB", "K", "BB", "ISO", "BABIP", "wRC", "age_rel", "pct"]
def stop(d): return {k: d[k] for k in keep if k in d}
def comp(c): return dict(name=c["name"], pos=c["pos"], tier=c["tier"], war=c["war"], harold=c["harold"],
                         active=c["active"], ab=c.get("ab"), stops={k: stop(v) for k, v in c["stops"].items()})
D = dict(name=r["name"], meta=meta, short=short, take10=take10, takewide=takewide,
         stops=[stop(x) for x in r["stops"]], comps=[comp(c) for c in r["comps"]], tally=r["tally"],
         wide=r["wide"], recent=[comp(c) for c in r["recent"]], order=r["order"], finger=r["finger"], method=method)

html = open("templates/prospect.html").read()
desc = f"The {n} minor leaguers who hit most like {r['name']} at the same age and level, and what they became."
html = html.replace("{{NAME}}", r["name"]).replace("{{DESC}}", desc).replace("{{INTRO}}", intro)
data = "const D=" + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";"
html = re.sub(r"^const D=.*;$", lambda _: data, html, count=1, flags=re.M)
os.makedirs(os.path.dirname(page), exist_ok=True)
open(page, "w").write(html)
print(page, len(html), "bytes")
print(short); print(take10); print(takewide); print(meta)
