"""Key-gated runners: youtube_trending, twitter_x_trends, producthunt_launches.
   Runs live when the matching secret env var is set, otherwise reports 'skipped'.
   Usage: stub.py <runner_id>"""

import json
import os
import sys
import urllib.request

from common import fetch, fetch_json, item, main, now_iso

KEYS = {
    "youtube_trending": "YOUTUBE_API_KEY",
    "twitter_x_trends": "X_API_BEARER",
    "producthunt_launches": "PRODUCTHUNT_TOKEN",
}


def youtube(runner_id):
    key = os.environ["YOUTUBE_API_KEY"]
    data = fetch_json(
        "https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet,statistics&chart=mostPopular&regionCode=US&maxResults=25&key={key}",
        timeout=40,
    )
    out = []
    for v in data.get("items", []):
        sn, st = v.get("snippet", {}), v.get("statistics", {})
        views = int(st.get("viewCount") or 0)
        score = min(95, 30 + (views ** 0.5) / 30)
        out.append(
            item(
                runner_id,
                "video",
                sn.get("title", ""),
                f"https://www.youtube.com/watch?v={v['id']}",
                score=score,
                published=sn.get("publishedAt"),
                tags=[sn.get("channelTitle", ""), "youtube"],
                metrics={"views": views, "likes": int(st.get("likeCount") or 0), "channel": sn.get("channelTitle", "")},
            )
        )
    return out


def twitter(runner_id):
    bearer = os.environ["X_API_BEARER"]
    req = urllib.request.Request(
        "https://api.twitter.com/2/trends/place?woeid=23424977&max_results=15",
        headers={"Authorization": f"Bearer {bearer}"},
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        data = json.loads(resp.read().decode("utf-8", "replace"))
    out = []
    for i, t in enumerate(data.get("data", [])[:15]):
        out.append(
            item(
                runner_id,
                "social",
                t.get("name", ""),
                f"https://x.com/search?q={t.get('name', '').replace(' ', '%20')}",
                score=max(40, 80 - i * 3),
                tags=["x-trends"],
                metrics={"rank": i + 1, "tweet_volume": t.get("tweet_volume")},
            )
        )
    return out


def producthunt(runner_id):
    token = os.environ["PRODUCTHUNT_TOKEN"]
    q = {
        "query": 'query { posts(order: RANKING, first: 25) { nodes { name tagline url votesCount createdAt } } }'
    }
    body = json.dumps(q).encode("utf-8")
    req = urllib.request.Request(
        "https://api.producthunt.com/v2/api/graphql",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        data = json.loads(resp.read().decode("utf-8", "replace"))
    out = []
    for p in data.get("data", {}).get("posts", {}).get("nodes", []):
        votes = p.get("votesCount") or 0
        score = min(90, 35 + votes * 0.6)
        out.append(
            item(
                runner_id,
                "startups",
                p.get("name", ""),
                p.get("url") or "",
                score=score,
                published=p.get("createdAt"),
                tags=["producthunt"],
                metrics={"votes": votes, "tagline": p.get("tagline") or ""},
            )
        )
    return out


if __name__ == "__main__":
    rid = sys.argv[1] if len(sys.argv) > 1 else "youtube_trending"
    fn = {"youtube_trending": youtube, "twitter_x_trends": twitter, "producthunt_launches": producthunt}.get(rid)
    if fn is None:
        print(f"[{rid}] unknown runner")
        sys.exit(1)
    main(rid, fn, args=[rid], needs_key=KEYS.get(rid))
