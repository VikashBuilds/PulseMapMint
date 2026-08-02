"""Run all 20 collectors locally, then aggregate. Usage: python scripts/run_all.py"""

import os
import subprocess
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "local_out")

RUNNERS = [
    ("hn_top", "hn.py", "hn_top top 30"),
    ("hn_best", "hn.py", "hn_best best 30"),
    ("hn_ask_show", "hn.py", "hn_ask_show ask_show 20"),
    ("reddit_all", "reddit.py", "reddit_all all world 25"),
    ("reddit_world_science", "reddit.py", "reddit_world_science worldnews,science,futurism,space world 25"),
    ("reddit_tech_startups", "reddit.py", "reddit_tech_startups technology,programming,startups,gadgets,artificial tech 25"),
    ("reddit_finance_crypto", "reddit.py", "reddit_finance_crypto stockmarket,investing,crypto,economicnews,wallstreetbets finance 25"),
    ("github_all", "github_trending.py", "github_all"),
    ("github_python_ts", "github_trending.py", "github_python_ts python typescript"),
    ("rss_world", "rss.py", "rss_world rss_world"),
    ("rss_tech", "rss.py", "rss_tech rss_tech"),
    ("rss_finance", "rss.py", "rss_finance rss_finance"),
    ("rss_science_space", "rss.py", "rss_science_space rss_science_space"),
    ("crypto_anomalies", "crypto.py", "crypto_anomalies 4 30"),
    ("stocks_movers", "stocks.py", "stocks_movers 2.5"),
    ("usgs_quakes", "usgs.py", "usgs_quakes 4.0"),
    ("weather_alerts", "weather.py", "weather_alerts"),
    ("youtube_trending", "stub.py", "youtube_trending"),
    ("twitter_x_trends", "stub.py", "twitter_x_trends"),
    ("producthunt_launches", "stub.py", "producthunt_launches"),
]


def main():
    for rid, module, args in RUNNERS:
        env = dict(os.environ)
        env["PULSEMAP_OUT"] = OUT
        cmd = [sys.executable, os.path.join(ROOT, "collectors", module)] + args.split()
        subprocess.run(cmd, env=env)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    subprocess.run(
        [
            sys.executable,
            os.path.join(ROOT, "scripts", "aggregate.py"),
            "--snapshots", OUT,
            "--data", os.path.join(ROOT, "data"),
            "--ts", ts,
        ]
    )


if __name__ == "__main__":
    main()
