"""Generate assets/stats.svg: a terminal-style `gh stats --me` card.

Data comes from GitHub's GraphQL API (needs GITHUB_TOKEN, which Actions provides).
Languages are summed over your own public, non-fork repositories, by code size.
For a local preview without a token:  python3 scripts/make_stats.py --sample
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

USER_LOGIN = os.environ.get("GH_USERNAME", "InspireKruthirao")
PROMPT_USER, HOST = "kruthi", "github"
YEAR = datetime.now(timezone.utc).year

QUERY = """
query ($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        nameWithOwner isFork stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
    }
  }
}
"""


def fetch():
    body = json.dumps({"query": QUERY, "variables": {
        "login": USER_LOGIN, "from": f"{YEAR}-01-01T00:00:00Z", "to": f"{YEAR}-12-31T23:59:59Z"}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.load(r)
    if res.get("errors"):
        sys.exit(f"GraphQL error: {res['errors'][0].get('message')}")
    return res["data"]["user"]


SAMPLE = {
    "followers": {"totalCount": 18}, "pullRequests": {"totalCount": 7}, "issues": {"totalCount": 3},
    "repositories": {"totalCount": 4, "nodes": [
        {"nameWithOwner": "InspireKruthirao/site", "isFork": False, "stargazerCount": 2, "languages": {"edges": [
            {"size": 52000, "node": {"name": "HTML", "color": "#e34c26"}},
            {"size": 21000, "node": {"name": "CSS", "color": "#663399"}},
            {"size": 9000, "node": {"name": "JavaScript", "color": "#f1e05a"}}]}},
        {"nameWithOwner": "InspireKruthirao/tool", "isFork": False, "stargazerCount": 1, "languages": {"edges": [
            {"size": 40000, "node": {"name": "Python", "color": "#3572A5"}},
            {"size": 3000, "node": {"name": "Shell", "color": "#89e051"}}]}},
    ]},
    "contributionsCollection": {"totalCommitContributions": 142, "restrictedContributionsCount": 96,
                                "contributionCalendar": {"totalContributions": 260}},
}

# ---------------------------------------------------------------- styling ---
W, CW, LH, PAD = 720, 8.4, 22, 24
C = dict(bg="#0d1117", bar="#161b22", border="#30363d", fg="#c9d1d9", dim="#6e7681",
         green="#3fb950", lime="#7ee787", blue="#79c0ff")


def t(x, y, s, color, bold=False, size=None, anchor=None):
    a = f' font-weight="700"' if bold else ""
    a += f' font-size="{size}"' if size else ""
    a += f' text-anchor="{anchor}"' if anchor else ""
    return f'<text x="{x:.1f}" y="{y}" fill="{color}"{a}>{escape(s)}</text>'


def build(user):
    own = [r for r in user["repositories"]["nodes"]
           if not r["isFork"] and r["nameWithOwner"].lower() != f"{USER_LOGIN}/{USER_LOGIN}".lower()]
    stars = sum(r["stargazerCount"] for r in user["repositories"]["nodes"] if not r["isFork"])
    langs = {}
    for r in own:
        for e in r["languages"]["edges"]:
            name = e["node"]["name"]
            size, color = langs.get(name, (0, e["node"]["color"] or C["dim"]))
            langs[name] = (size + e["size"], color)
    total = sum(s for s, _ in langs.values())
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])
    if len(top) > 5:
        other = sum(s for _, (s, _) in top[5:])
        top = top[:5] + [("Other", (other, C["dim"]))]

    cc = user["contributionsCollection"]
    stats = [
        (f"Contributions {YEAR}", cc["contributionCalendar"]["totalContributions"]),
        (f"Commits {YEAR}", cc["totalCommitContributions"] + 0),
        ("Private contribs", cc["restrictedContributionsCount"]),
        ("Pull requests", user["pullRequests"]["totalCount"]),
        ("Issues", user["issues"]["totalCount"]),
        ("Public repos", user["repositories"]["totalCount"]),
        ("Stars earned", stars),
        ("Followers", user["followers"]["totalCount"]),
    ]

    out = []
    y0 = 60
    # prompt
    x = PAD
    for s, col, b in [(PROMPT_USER, C["green"], True), ("@", C["dim"], False), (HOST, C["green"], True),
                      (":", C["dim"], False), ("~", C["blue"], True), ("$ ", C["dim"], False),
                      ("gh stats --me", C["fg"], False)]:
        out.append(t(x, y0, s, col, b))
        x += len(s) * CW

    # left column: numbers
    y = y0 + LH + 10
    out.append(t(PAD, y, "# activity", C["dim"]))
    for label, val in stats:
        y += LH
        out.append(t(PAD, y, f"{label:<17}", C["green"], True))
        out.append(t(PAD + 18 * CW, y, f"{val:>6,}", C["fg"]))
    left_bottom = y

    # right column: languages
    RX = 380
    y = y0 + LH + 10
    out.append(t(RX, y, "# languages (own public repos)", C["dim"]))
    y += 16
    bar_w = W - RX - PAD
    if total:
        bx = RX
        out.append(f'<clipPath id="bar"><rect x="{RX}" y="{y}" width="{bar_w}" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">')
        for name, (size, color) in top:
            w = bar_w * size / total
            out.append(f'<rect x="{bx:.1f}" y="{y}" width="{w + 0.5:.1f}" height="10" fill="{color}"/>')
            bx += w
        out.append("</g>")
        y += 10
        for name, (size, color) in top:
            y += LH
            out.append(f'<circle cx="{RX + 5}" cy="{y - 5}" r="5" fill="{color}"/>')
            out.append(t(RX + 18, y, name, C["fg"]))
            out.append(t(W - PAD, y, f"{100 * size / total:5.1f}%", C["dim"], anchor="end"))
    else:
        y += LH
        out.append(t(RX, y, "no public code yet", C["dim"]))

    H = max(left_bottom, y) + 26

    alt = "GitHub stats: " + ", ".join(f"{k} {v}" for k, v in stats) + ". Languages: " + (
        ", ".join(f"{n} {100 * s / total:.0f}%" for n, (s, _) in top) if total else "none") + "."
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="title" xml:space="preserve">
<title id="title">{escape(alt)}</title>
<style>text {{ font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace; font-size: 14px; white-space: pre; }}</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="{C["bg"]}" stroke="{C["border"]}"/>
<path d="M0.5 32 V10.5 a10 10 0 0 1 10 -10 H{W - 10.5} a10 10 0 0 1 10 10 V32 Z" fill="{C["bar"]}"/>
<line x1="0.5" y1="32" x2="{W - 0.5}" y2="32" stroke="{C["border"]}"/>
<circle cx="20" cy="16" r="6" fill="#ff5f57"/><circle cx="40" cy="16" r="6" fill="#febc2e"/><circle cx="60" cy="16" r="6" fill="#28c840"/>
{t(W / 2, 21, f"{PROMPT_USER}@{HOST}: ~ — gh stats", C["dim"], size=12, anchor="middle")}
{"".join(out)}
</svg>
'''


if __name__ == "__main__":
    user = SAMPLE if "--sample" in sys.argv else fetch()
    path = Path(__file__).resolve().parent.parent / "assets" / "stats.svg"
    path.write_text(build(user), encoding="utf-8")
    print(f"wrote {path}")
