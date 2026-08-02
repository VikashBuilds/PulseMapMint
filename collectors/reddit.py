"""Reddit rising-post runner. Usage: reddit.py <runner_id> <subreddit_list> <category> [limit]
Optionally authenticates when REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET env vars are set
(free Reddit app credentials make the API far more reliable from cloud IPs)."""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

from common import fetch_json, heat_from_log, item, main

BASE = "https://api.reddit.com"
CLIENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
TOKEN_CACHE = {}


def get_token():
    cid, sec = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if not cid or not sec:
        return None
    if TOKEN_CACHE.get("token"):
        return TOKEN_CACHE["token"]
    data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(
        "https://www.reddit.com/api/v1/access_token",
        data=data,
        headers={"User-Agent": f"pulsemap-radar/1.0 by {cid}", "Authorization": "Basic " + __import__("base64").b64encode(f"{cid}:{sec}".encode()).decode()},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        TOKEN_CACHE["token"] = json.loads(resp.read())["access_token"]
    return TOKEN_CACHE["token"]


def fetch_rising(subs, limit):
    token = get_token()
    url = f"{BASE}/r/{subs}/rising?limit={limit}"
    headers = {"User-Agent": CLIENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last = None
    for attempt in range(3):
        try:
            return fetch_json(url, headers=headers)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def collect(runner_id, subreddits, category, limit):
    limit = int(limit)
    subs = subreddits.replace(",", "+")
    data = fetch_rising(subs, limit)
    out = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        if not d.get("title"):
            continue
        out.append(
            item(
                runner_id,
                category,
                d["title"],
                "https://www.reddit.com" + (d.get("permalink") or ""),
                score=heat_from_log(d.get("score") or 0),
                published=d.get("created_utc") or time.time(),
                tags=[d.get("subreddit", ""), "reddit"],
                metrics={
                    "ups": d.get("ups") or 0,
                    "comments": d.get("num_comments") or 0,
                    "subreddit": d.get("subreddit", ""),
                },
            )
        )
    return out


if __name__ == "__main__":
    rid = sys.argv[1] if len(sys.argv) > 1 else "reddit_all"
    main(rid, collect, args=[rid] + (sys.argv[2:] or ["all", "world", "25"]))
