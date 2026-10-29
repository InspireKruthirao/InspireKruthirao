"""Generate assets/terminal.svg: the animated neofetch-style card at the top of the README.

Edit the PROFILE / PLAN lists below and run:  python3 scripts/make_terminal.py
"""
import math
from html import escape
from pathlib import Path

USER, HOST = "kruthi", "github"

PROFILE = [  # (label, value) shown next to the helix
    ("Name", "Nithya Kruthi Macha"),
    ("Field", "Bioinformatics & Comp Bio"),
    ("Lab", "@BigDataBiology"),
    ("Focus", "Microbiomes x big data"),
    ("Lang", "Python, Bash, R"),
    ("Base", "Australia"),
    ("Web", "inspirekruthirao.github.io"),
    ("ORCID", "0000-0002-4149-0400"),
]

PLAN = [  # (mark, text) for `cat ~/.plan`; mark: "x" done, "~" in progress
    ("x", "turn sequencing data into biology"),
    ("x", "contribute to open-source science"),
    ("~", "keep learning, keep sharing  ->  inspirekruthirao.github.io"),
]

# ---------------------------------------------------------------- layout ---
W = 720
CW = 8.4            # monospace character width at 14px
LH = 20             # line height
PAD = 24
TOP = 60            # baseline of first prompt line
INFO_X = 250        # x where neofetch info column starts

C = dict(bg="#0d1117", bar="#161b22", border="#30363d", fg="#c9d1d9", dim="#6e7681",
         green="#3fb950", lime="#7ee787", blue="#79c0ff", yellow="#e3b341",
         pink="#ff7b72", purple="#d2a8ff")


def xs(x0, text):
    return " ".join(f"{x0 + i * CW:.1f}" for i in range(len(text)))


def span(text, color, x0=None, bold=False):
    attrs = f'fill="{color}"' + (' font-weight="700"' if bold else "")
    if x0 is not None:
        attrs += f' x="{xs(x0, text)}"'
    return f"<tspan {attrs}>{escape(text)}</tspan>"


def show(t):
    return f'<set attributeName="visibility" to="visible" begin="{t:.3f}s" fill="freeze"/>'


def prompt_spans(x0=PAD):
    out, x = [], x0
    for text, color, bold in [(USER, C["green"], True), ("@", C["dim"], False),
                              (HOST, C["green"], True), (":", C["dim"], False),
                              ("~", C["blue"], True), ("$ ", C["dim"], False)]:
        out.append(span(text, color, x, bold))
        x += len(text) * CW
    return "".join(out), x


clips, body = [], []


def typed_command(y, cmd, t_show, t_type, cid, cursor_hide=True):
    """Prompt appears at t_show; cmd types out from t_type. Returns end time."""
    ps, cx = prompt_spans()
    body.append(f'<text y="{y}" visibility="hidden">{ps}{show(t_show)}</text>')
    dur = 0.075 * len(cmd)
    widths = ";".join(f"{(i + 1) * CW:.1f}" for i in range(len(cmd)))
    keys = ";".join(f"{i / max(len(cmd) - 1, 1):.3f}" for i in range(len(cmd)))
    clips.append(f'<clipPath id="{cid}"><rect x="{cx:.1f}" y="{y - 16}" width="0" height="24">'
                 f'<animate attributeName="width" values="{widths}" calcMode="discrete" '
                 f'keyTimes="{keys}" begin="{t_type:.3f}s" dur="{dur:.3f}s" fill="freeze"/></rect></clipPath>')
    body.append(f'<text y="{y}" clip-path="url(#{cid})">{span(cmd, C["fg"], cx)}</text>')
    curx = ";".join(f"{cx + (i + 1) * CW:.1f}" for i in range(len(cmd)))
    end = t_type + dur
    hide = f'<set attributeName="visibility" to="hidden" begin="{end + 0.35:.3f}s" fill="freeze"/>' if cursor_hide else ""
    body.append(f'<rect x="{cx:.1f}" y="{y - 12}" width="{CW}" height="17" fill="{C["lime"]}" visibility="hidden">'
                f'{show(t_show)}<animate attributeName="x" values="{curx}" calcMode="discrete" keyTimes="{keys}" '
                f'begin="{t_type:.3f}s" dur="{dur:.3f}s" fill="freeze"/>{hide}</rect>')
    return end + 0.35


def helix_frame(phase, rows=11, cx=PAD + 9 * CW):
    """One frame of an ASCII double helix as a list of (x, y, char, color)."""
    bases = "ATCGGCTAAGCTTAGC"
    pairs = {"A": "T", "T": "A", "C": "G", "G": "C"}
    pts = []
    for r in range(rows):
        a = r * 0.62 + phase
        w = round(6 * math.sin(a))
        y = TOP + LH + r * LH
        l, rr = cx - w * CW, cx + w * CW
        front_left = math.cos(a) > 0
        if w == 0:
            pts.append((cx, y, "X", C["purple"]))
            continue
        b = bases[r % len(bases)]
        lo, hi = (l, rr) if l < rr else (rr, l)
        pts.append((lo, y, b if front_left else pairs[b], C["lime"] if front_left else C["green"]))
        pts.append((hi, y, pairs[b] if front_left else b, C["green"] if front_left else C["lime"]))
        n = int(round((hi - lo) / CW)) - 1
        for k in range(1, n + 1):
            pts.append((lo + k * CW, y, "-" if abs(w) > 1 else "=", C["dim"]))
    return pts


def helix_svg(t_show):
    frames = [helix_frame(p) for p in (0.0, math.pi / 3, 2 * math.pi / 3)]
    out = []
    for i, pts in enumerate(frames):
        cells = "".join(f'<text x="{x:.1f}" y="{y}" fill="{c}" font-weight="700">{escape(ch)}</text>'
                        for x, y, ch, c in pts)
        out.append(f'<g class="f{i}">{cells}</g>')
    return f'<g visibility="hidden">{show(t_show)}{"".join(out)}</g>'


# --------------------------------------------------------------- timeline ---
t = typed_command(TOP, "neofetch", 0.4, 1.0, "c0")
body.append(helix_svg(t))

info_y = TOP + LH
lines = [[(f"{USER}", C["lime"], True), ("@", C["fg"], False), (HOST, C["lime"], True)],
         [("-" * (len(USER) + len(HOST) + 1), C["dim"], False)]]
for label, value in PROFILE:
    lines.append([(f"{label + ':':<8}", C["green"], True), (value, C["fg"], False)])
for i, segs in enumerate(lines):
    t += 0.05
    s = "".join(span(txt, col, bold=b) for txt, col, b in segs)
    body.append(f'<text x="{INFO_X}" y="{info_y + i * LH}" visibility="hidden">{s}{show(t)}</text>')

t += 0.12
sw_y = info_y + len(lines) * LH + 4
for i, col in enumerate([C["pink"], C["yellow"], C["green"], C["blue"], C["purple"], C["fg"]]):
    body.append(f'<rect x="{INFO_X + i * 26}" y="{sw_y}" width="22" height="12" rx="2" fill="{col}" visibility="hidden">{show(t)}</rect>')

y = max(sw_y + 12, TOP + LH * 12) + 34
t = typed_command(y, "cat ~/.plan", t + 0.5, t + 1.1, "c1")
for mark, text in PLAN:
    y += LH
    t += 0.12
    s = (span("[", C["dim"]) + span(mark, C["green"] if mark == "x" else C["yellow"], bold=True)
         + span("] ", C["dim"]) + span(text, C["fg"]))
    body.append(f'<text x="{PAD}" y="{y}" visibility="hidden">{s}{show(t)}</text>')

y += LH
t += 0.5
ps, cx = prompt_spans()
body.append(f'<text y="{y}" visibility="hidden">{ps}{show(t)}</text>')
body.append(f'<rect x="{cx:.1f}" y="{y - 12}" width="{CW}" height="17" fill="{C["lime"]}" visibility="hidden">{show(t)}'
            f'<animate attributeName="opacity" values="1;0" dur="1.1s" calcMode="discrete" begin="{t:.3f}s" repeatCount="indefinite"/></rect>')

H = y + 26
title = f"{USER}@{HOST}: ~ — zsh"
alt = (f"{USER}@{HOST}:~$ neofetch. " + ". ".join(f"{k}: {v}" for k, v in PROFILE) + ". "
       + " ".join(t for _, t in PLAN))

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="title" xml:space="preserve">
<title id="title">{escape(alt)}</title>
<style>
text {{ font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace; font-size: 14px; white-space: pre; }}
.title {{ fill: {C["dim"]}; font-size: 12px; }}
@keyframes a0 {{ 0%,33.32% {{ opacity: 1; }} 33.33%,100% {{ opacity: 0; }} }}
@keyframes a1 {{ 0%,33.32% {{ opacity: 0; }} 33.33%,66.65% {{ opacity: 1; }} 66.66%,100% {{ opacity: 0; }} }}
@keyframes a2 {{ 0%,66.65% {{ opacity: 0; }} 66.66%,100% {{ opacity: 1; }} }}
.f0 {{ animation: a0 1.5s infinite; }} .f1 {{ animation: a1 1.5s infinite; }} .f2 {{ animation: a2 1.5s infinite; }}
@media (prefers-reduced-motion: reduce) {{ .f0 {{ animation: none; }} .f1, .f2 {{ animation: none; opacity: 0; }} }}
</style>
<defs>{"".join(clips)}</defs>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="{C["bg"]}" stroke="{C["border"]}"/>
<path d="M0.5 32 V10.5 a10 10 0 0 1 10 -10 H{W - 10.5} a10 10 0 0 1 10 10 V32 Z" fill="{C["bar"]}"/>
<line x1="0.5" y1="32" x2="{W - 0.5}" y2="32" stroke="{C["border"]}"/>
<circle cx="20" cy="16" r="6" fill="#ff5f57"/><circle cx="40" cy="16" r="6" fill="#febc2e"/><circle cx="60" cy="16" r="6" fill="#28c840"/>
<text class="title" x="{W / 2}" y="21" text-anchor="middle">{escape(title)}</text>
{"".join(body)}
</svg>
'''

out = Path(__file__).resolve().parent.parent / "assets" / "terminal.svg"
out.parent.mkdir(exist_ok=True)
out.write_text(svg, encoding="utf-8")
print(f"wrote {out} ({len(svg)} bytes, {W}x{H})")
