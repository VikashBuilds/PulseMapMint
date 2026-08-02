"""HackerNews runners: top, best, ask+show. Usage: hn.py <runner_id> <list> [limit]"""

import sys

from common import fetch_json, heat_from_log, item, main

BASE = "https://hacker-news.firebaseio.com/v0"
LISTS = {
    "top": "topstories.json",
    "best": "beststories.json",
    "ask": "askstories.json",
    "show": "showstories.json",
}


def collect(runner_id, list_name, limit):
    limit = int(limit)
    ids = fetch_json(f"{BASE}/{LISTS[list_name]}")[:limit]
    stories = fetch_json_many(ids)
    out = []
    for story in stories:
        if not story or not story.get("title"):
            continue
        url = story.get("url") or f"https://news.ycombinator.com/item?id={story['id']}"
        out.append(
            item(
                runner_id,
                "tech",
                story["title"],
                url,
                score=heat_from_log(story.get("score") or 0),
                published=story.get("time"),
                tags=["hackernews"],
                metrics={
                    "points": story.get("score") or 0,
                    "comments": story.get("descendants") or 0,
                    "hn_id": story["id"],
                },
            )
        )
    return out


def fetch_json_many(ids):
    import concurrent.futures as cf

    out = []
    with cf.ThreadPoolExecutor(max_workers=12) as pool:
        futs = {pool.submit(fetch_json, f"{BASE}/item/{i}.json"): i for i in ids}
        for fut in cf.as_completed(futs):
            try:
                out.append(fut.result())
            except Exception:  # noqa: BLE001
                pass
    return out


def ask_show(runner_id, *_):
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    return collect(runner_id, "ask", limit) + collect(runner_id, "show", limit)


if __name__ == "__main__":
    rid = sys.argv[1] if len(sys.argv) > 1 else "hn_top"
    if len(sys.argv) > 2 and sys.argv[2] == "ask_show":
        main(rid, ask_show)
    else:
        main(rid, collect)
