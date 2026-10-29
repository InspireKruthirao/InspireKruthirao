"""Patch Platane/snk so it fetches the contribution grid for a date range.

The upstream action always uses the rolling last 12 months. This adds the
GraphQL `from`/`to` arguments, read from SNAKE_FROM / SNAKE_TO env vars.
Fails loudly if the upstream code no longer matches, so a silent no-op can't happen.

Usage: python3 scripts/patch_snk.py <path-to-snk-checkout>
"""
import sys
from pathlib import Path

target = Path(sys.argv[1]) / "packages/github-user-contribution/index.ts"
src = target.read_text(encoding="utf-8")

edits = [
    ("query ($login: String!) {",
     "query ($login: String!, $from: DateTime, $to: DateTime) {"),
    ("contributionsCollection {",
     "contributionsCollection(from: $from, to: $to) {"),
    ("const variables = { login: userName };",
     "const variables = { login: userName, from: process.env.SNAKE_FROM || null, to: process.env.SNAKE_TO || null };"),
]
for old, new in edits:
    if src.count(old) != 1:
        sys.exit(f"patch_snk: expected exactly one occurrence of {old!r} in {target}")
    src = src.replace(old, new)

target.write_text(src, encoding="utf-8")
print(f"patched {target}")
