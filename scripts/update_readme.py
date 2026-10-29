"""Refresh the live sections of README.md from public GitHub data.

  * REPO-LIST   -> most recently pushed public repositories
  * activity    -> recent public events (pushes, forks, stars, PRs, issues...)

Runs in GitHub Actions (needs GH_USERNAME, optionally GITHUB_TOKEN).
Only the text between each pair of markers is rewritten.
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

USER = os.environ["GH_USERNAME"]
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = os.environ.get("TARGET_FILE", "README.md")
MAX_REPOS = int(os.environ.get("MAX_REPOS", "5"))
MAX_EVENTS = int(os.environ.get("MAX_EVENTS", "6"))
PROFILE_REPO = f"{USER}/{USER}".lower()


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Accept": "application/vnd.github+json",
                 **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def link(name):
    return f"[{name}](https://github.com/{name})"


# ------------------------------------------------------------- repo list ---
def repo_lines():
    out = []
    for r in api(f"/users/{USER}/repos?sort=pushed&per_page=30&type=owner"):
        if r["full_name"].lower() == PROFILE_REPO or r.get("private"):
            continue
        tag = " `fork`" if r.get("fork") else ""
        desc = (r.get("description") or "").strip()
        desc = f" · {desc}" if desc else ""
        if len(desc) > 90:
            desc = desc[:87].rstrip() + "…"
        out.append(f"- `{r['pushed_at'][:10]}` [{r['name']}]({r['html_url']}){tag}{desc}")
        if len(out) >= MAX_REPOS:
            break
    return out or ["- _nothing public yet_"]


# -------------------------------------------------------------- activity ---
def describe(ev):
    t, repo, p = ev["type"], ev["repo"]["name"], ev.get("payload", {})
    if repo.lower() == PROFILE_REPO:
        return None
    if t == "PushEvent":
        n = p.get("size") or len(p.get("commits") or [])
        return f"⬆️ pushed {n} commit{'s' if n != 1 else ''} to {link(repo)}" if n else f"⬆️ pushed to {link(repo)}"
    if t == "CreateEvent" and p.get("ref_type") == "repository":
        return f"🆕 created {link(repo)}"
    if t == "CreateEvent" and p.get("ref_type") == "branch":
        return f"🌿 branched `{p.get('ref')}` in {link(repo)}"
    if t == "ForkEvent":
        return f"🍴 forked {link(repo)}"
    if t == "WatchEvent":
        return f"⭐ starred {link(repo)}"
    if t == "PullRequestEvent":
        pr = p.get("pull_request", {})
        act = "merged" if p.get("action") == "closed" and pr.get("merged") else p.get("action", "")
        return f"🔀 {act} PR [#{pr.get('number')}]({pr.get('html_url')}) in {link(repo)}"
    if t == "IssuesEvent":
        i = p.get("issue", {})
        return f"❗ {p.get('action', '')} issue [#{i.get('number')}]({i.get('html_url')}) in {link(repo)}"
    if t == "IssueCommentEvent":
        i = p.get("issue", {})
        return f"🗣 commented on [#{i.get('number')}]({p.get('comment', {}).get('html_url')}) in {link(repo)}"
    if t == "ReleaseEvent":
        rel = p.get("release", {})
        return f"🚀 released [{rel.get('tag_name')}]({rel.get('html_url')}) in {link(repo)}"
    return None


def activity_lines():
    out, seen = [], set()
    for ev in api(f"/users/{USER}/events/public?per_page=100"):
        text = describe(ev)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(f"- `{ev['created_at'][:10]}` {text}")
        if len(out) >= MAX_EVENTS:
            break
    return out or ["- _no recent public activity — check back soon_"]


# ----------------------------------------------------------------- write ---
def replace(content, start, end, lines):
    return re.sub(re.escape(start) + r".*?" + re.escape(end),
                  lambda _: start + "\n" + "\n".join(lines) + "\n" + end, content, flags=re.S)


def main():
    with open(README, encoding="utf-8") as f:
        content = f.read()
    new = replace(content, "<!-- REPO-LIST:START -->", "<!-- REPO-LIST:END -->", repo_lines())
    new = replace(new, "<!--START_SECTION:activity-->", "<!--END_SECTION:activity-->", activity_lines())
    # keep the snake heading's year in step with the snake workflow (current calendar year)
    new = re.sub(r"(snake --eat ~/contributions --year )\d{4}",
                 lambda m: m.group(1) + str(datetime.now(timezone.utc).year), new)
    if new != content:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)
        print("README updated.")
    else:
        print("No change.")


if __name__ == "__main__":
    main()
