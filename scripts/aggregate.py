"""Merge runner snapshots into the git data store.
Usage: python scripts/aggregate.py --snapshots <dir> --data <dir> [--ts <timestamp>]
"""

import argparse
import glob
import json
import os
import re
import sys
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "collectors"))

HISTORY_LIMIT = 400
TOP_LIMIT = 120
RUNNER_LABELS = {
    "hn_top": "HackerNews Top",
    "hn_best": "HackerNews Best",
    "hn_ask_show": "HN Ask + Show",
    "reddit_all": "Reddit r/all Rising",
    "reddit_world_science": "Reddit World/Science",
    "reddit_tech_startups": "Reddit Tech/Startups",
    "reddit_finance_crypto": "Reddit Finance/Crypto",
    "github_all": "GitHub Trending",
    "github_python_ts": "GitHub Py/TS",
    "rss_world": "RSS World News",
    "rss_tech": "RSS Tech/AI",
    "rss_finance": "RSS Finance",
    "rss_science_space": "RSS Science/Space",
    "crypto_anomalies": "Crypto Anomalies",
    "stocks_movers": "Stock Movers",
    "usgs_quakes": "USGS Earthquakes",
    "weather_alerts": "Weather Alerts",
    "youtube_trending": "YouTube Trending",
    "twitter_x_trends": "X/Twitter Trends",
    "producthunt_launches": "Product Hunt",
}


def norm_key(title):
    return re.sub(r"[^a-z0-9]", "", (title or "").lower())[:80]


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots", default="out")
    ap.add_argument("--data", default="data")
    ap.add_argument("--ts", default=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.snapshots, "*.json")))
    if not files:
        print("no snapshots found")
        sys.exit(1)

    runners = {}
    items = []
    watch = {}
    for f in files:
        p = load(f)
        rid = p["runner"]
        runners[rid] = {
            "label": RUNNER_LABELS.get(rid, rid),
            "status": p.get("status"),
            "items": len(p.get("items") or []),
            "took_s": p.get("took_s"),
            "generated": p.get("generated"),
            "error": p.get("error"),
        }
        if isinstance(p.get("watch"), dict):
            watch.update(p["watch"])
        for it in p.get("items") or []:
            it["source"] = rid
            items.append(it)

    seen = {}
    for it in items:
        k = norm_key(it.get("title"))
        if k in seen:
            cur = seen[k]
            if it.get("score", 0) > cur.get("score", 0):
                seen[k] = it
        else:
            seen[k] = it
    items = list(seen.values())

    now = datetime.datetime.now(datetime.timezone.utc)
    for it in items:
        age_s = now.timestamp()
        try:
            pub = it.get("published") or ""
            dt = datetime.datetime.fromisoformat(pub.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            age_s = (now - dt).total_seconds()
        except (ValueError, TypeError):
            pass
        boost = 0
        if age_s < 1800:
            boost = 15
        elif age_s < 7200:
            boost = 8
        elif age_s < 21600:
            boost = 3
        it["heat"] = round(min(100.0, float(it.get("score", 0)) + boost), 1)
        it["age_s"] = max(0, int(age_s))
        it.pop("score", None)

    items.sort(key=lambda x: -x["heat"])
    top = items[:TOP_LIMIT]

    counts = {}
    for it in items:
        counts[it["category"]] = counts.get(it["category"], 0) + 1
    breakers = sum(1 for it in top if it["heat"] >= 70)

    ts = args.ts
    snapshot_dir = os.path.join(args.data, "snapshots", ts)
    run_dir = os.path.join(snapshot_dir, "runners")
    for f in files:
        rid = os.path.splitext(os.path.basename(f))[0]
        with open(f, encoding="utf-8") as fh:
            raw = fh.read()
        os.makedirs(run_dir, exist_ok=True)
        with open(os.path.join(run_dir, f"{rid}.json"), "w", encoding="utf-8") as fh:
            fh.write(raw)
    save(os.path.join(snapshot_dir, "all.json"), {"ts": ts, "generated": now.isoformat(), "items": top})

    meta = {
        "ts": ts,
        "generated": now.isoformat(),
        "total_events": len(items),
        "breakers": breakers,
        "categories": counts,
        "runners": runners,
        "watch": watch,
    }
    save(os.path.join(args.data, "latest", "all.json"), {"ts": ts, "generated": now.isoformat(), "items": top})
    save(os.path.join(args.data, "latest", "meta.json"), meta)

    history_path = os.path.join(args.data, "history.json")
    history = load(history_path) if os.path.exists(history_path) else []
    history.append(
        {
            "ts": ts,
            "generated": now.isoformat(),
            "events": len(items),
            "breakers": breakers,
            "avg_heat": round(sum(it["heat"] for it in top) / max(1, len(top)), 1),
            "prices": watch,
            "top": [{"t": it["title"][:90], "s": it["source"], "h": it["heat"], "c": it["category"]} for it in top[:10]],
        }
    )
    history = history[-HISTORY_LIMIT:]
    save(history_path, history)

    ok = sum(1 for r in runners.values() if r["status"] == "ok")
    print(f"aggregate {ts}: runners={len(runners)} ok={ok} events={len(items)} top={len(top)} breakers={breakers}")
    for rid, r in sorted(runners.items()):
        flag = " " if r["status"] == "ok" else "!"
        print(f"  {flag} {rid:24s} {r['status']:8s} items={r['items']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
