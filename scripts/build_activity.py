#!/usr/bin/env python3
"""Build a public, year-by-year activity dataset for the indkhan profile site."""
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OWNER = "indkhan"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"
HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
if TOKEN:
    HEADERS["Authorization"] = "Bearer " + TOKEN

def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=35) as response:
                return json.load(response), response.headers
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < 4:
                reset = int(e.headers.get("X-RateLimit-Reset", "0"))
                wait = max(2, min(60, reset - int(time.time()))) if reset else 8 * (attempt + 1)
                time.sleep(wait)
                continue
            raise

def pages(url):
    while url:
        data, headers = get_json(url)
        if not isinstance(data, list):
            raise RuntimeError("Expected a list from GitHub API: " + url)
        yield from data
        link = headers.get("Link", "")
        url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part[part.find("<")+1:part.find(">")]
                break

def all_days(year):
    d = dt.date(year, 1, 1)
    end = dt.date(year, 12, 31)
    while d <= end:
        yield d.isoformat()
        d += dt.timedelta(days=1)

def main():
    today = dt.date.today()
    years = list(range(max(2008, today.year - 6), today.year + 1))
    daily = {y: {k: {"contributions": 0, "commits": 0} for k in all_days(y)} for y in years}
    contributions_total = {y: 0 for y in years}
    # Contributions calendar is returned by GitHub's GraphQL API, separately from commit counts.
    query = """query($login:String!, $from:DateTime!, $to:DateTime!) {
      user(login:$login) {
        contributionsCollection(from:$from,to:$to) {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }"""
    for y in years:
        variables = {"login": OWNER, "from": f"{y}-01-01T00:00:00Z", "to": f"{y}-12-31T23:59:59Z"}
        body = json.dumps({"query": query, "variables": variables}).encode()
        req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={**HEADERS, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=35) as response:
                result = json.load(response)
            if result.get("errors"):
                raise RuntimeError(str(result["errors"]))
            cal = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
            contributions_total[y] = cal["totalContributions"]
            for week in cal["weeks"]:
                for day in week["contributionDays"]:
                    key = day["date"]
                    if key in daily[y]:
                        daily[y][key]["contributions"] = day["contributionCount"]
        except Exception as e:
            print(f"WARNING: GraphQL contributions for {y} unavailable: {e}")
    # Count commits authored by this GitHub account in repositories owned by the account.
    repos = list(pages(f"{API}/users/{OWNER}/repos?type=owner&per_page=100&sort=full_name"))
    owned = [r for r in repos if not r.get("fork") and not r.get("archived")]
    repo_counts = {y: {} for y in years}
    errors = []
    for repo in owned:
        full_name = repo["full_name"]
        for y in years:
            since, until = f"{y}-01-01T00:00:00Z", f"{y+1}-01-01T00:00:00Z"
            url = f"{API}/repos/{full_name}/commits?author={OWNER}&since={urllib.parse.quote(since)}&until={urllib.parse.quote(until)}&per_page=100"
            try:
                for commit in pages(url):
                    date = (commit.get("commit", {}).get("author", {}).get("date") or "")[:10]
                    if date in daily[y]:
                        daily[y][date]["commits"] += 1
                        repo_counts[y][full_name] = repo_counts[y].get(full_name, 0) + 1
            except urllib.error.HTTPError as e:
                if e.code not in (409, 404):
                    errors.append(f"{full_name} {y}: HTTP {e.code}")
            except Exception as e:
                errors.append(f"{full_name} {y}: {e}")
    out = {"username": OWNER, "updatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "years": {}}
    for y in years:
        days = list(daily[y].keys())
        cby = {k: daily[y][k]["contributions"] for k in days}
        mby = {k: daily[y][k]["commits"] for k in days}
        repositories = [{"name": name.split("/", 1)[1], "url": f"https://github.com/{name}", "commits": count}
                        for name, count in sorted(repo_counts[y].items(), key=lambda item: (-item[1], item[0].lower()))]
        out["years"][str(y)] = {
            "days": days, "contributionsByDay": cby, "commitsByDay": mby,
            "contributionsTotal": contributions_total[y], "commitsTotal": sum(mby.values()),
            "repositories": repositories, "complete": not errors
        }
    Path("activity").mkdir(exist_ok=True)
    Path("activity/data.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote activity/data.json for {len(years)} years; repository API warnings: {len(errors)}")
    if errors:
        print("\n".join(errors[:30]))

if __name__ == "__main__":
    main()
