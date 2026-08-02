# 🌍 PulseMap — Real-Time Global Event Radar

A mission-control dashboard that watches the entire internet for breaking events,
trending topics, viral content, and market movements **before they hit mainstream
news** — with 20 parallel sensors, a git-committed JSON data store, and a live
GitHub Pages dashboard. Zero server costs, zero API keys required for the core.

```
20 runners scraping in parallel (GitHub Actions matrix):

  HN Top · HN Best · HN Ask+Show
  Reddit r/all · Reddit World/Science · Reddit Tech/Startups · Reddit Finance/Crypto
  GitHub Trending · GitHub Py/TS
  RSS World (14 feeds) · RSS Tech/AI (13) · RSS Finance (9) · RSS Science/Space (9)
  Crypto Anomalies (CoinGecko) · Stock Movers (Yahoo) · USGS Earthquakes · NWS Alerts
  YouTube Trending* · X/Twitter Trends* · Product Hunt*  (*key-gated)

        ↓  each runner writes one JSON snapshot
        ↓
  aggregate → data/snapshots/<ts>/  (full git history = data store)
            → data/latest/all.json + meta.json (dashboard + free API)
            → data/history.json (rolling 400-sweep telemetry)
        ↓
  GitHub Pages renders the mission-control dashboard
```

**Why it's magical:** trends hit PulseMap 2–6 hours before mainstream media.
Built for traders, content creators, and journalists. The `data/` directory IS
the product — it ships as a free API layer out of the box.

---

## Quickstart (local, no GitHub needed)

```powershell
python scripts\run_all.py      # runs all 20 collectors + aggregate
python -m http.server 8080     # serve from the project root
# open http://localhost:8080/site/
```

## Deploy (10 minutes, costs nothing)

1. Create a **public** GitHub repo (public = unlimited Actions minutes) and push:

   ```powershell
   git init && git add . && git commit -m "PulseMap initial"
   git remote add origin https://github.com/<you>/PulseMap.git
   git push -u origin main
   ```

2. Repo **Settings → Pages → Build and deployment → Source: GitHub Actions**.

3. Trigger a run: **Actions → PulseMap Radar → Run workflow** (the schedule is
   `0 */2 * * *` — every 2 hours; edit `radar.yml` to change frequency).

4. Dashboard goes live at
   `https://<you>.github.io/PulseMap/` — the workflow prints the URL.

> ⚠️ **Public repo only.** 20 parallel jobs ≈ 20 minutes per sweep. A private
> repo gets 2,000 min/month free (≈ 5 sweeps/day) — a public repo is unlimited.

## Optional API keys (GitHub → Settings → Secrets → Actions)

| Secret | Runner | Get it |
|---|---|---|
| `YOUTUBE_API_KEY` | YouTube trending | Google Cloud console (free) |
| `X_API_BEARER` | X/Twitter trends | X Developer API (paid) |
| `PRODUCTHUNT_TOKEN` | Product Hunt launches | producthunt.com API (free) |
| `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | Reddit (recommended) | reddit.com → apps → script app (free, 5 min) |

Without keys, runners report `KEY NEEDED` on the dashboard and everything else
keeps running. Reddit works anonymously but is sometimes blocked from cloud IPs
— the free OAuth pair fixes that.

## The data store is the API

Every JSON file on `gh-pages` is a free, CORS-enabled endpoint. Example with
`<you>` as owner and `<repo>` as repo name:

```bash
# Top 120 events with heat scores, this sweep
curl https://<you>.github.io/<repo>/data/latest/all.json

# Runner health + category counts + crypto watch prices
curl https://<you>.github.io/<repo>/data/latest/meta.json

# Rolling telemetry (event volume, avg heat, BTC/ETH/SOL prices, top stories)
curl https://<you>.github.io/<repo>/data/history.json

# Full immutable snapshots per sweep (git history = unlimited retention)
curl https://<you>.github.io/<repo>/data/snapshots/20260802T124927Z/all.json
```

Item schema:

```json
{
  "id": "a1b2c3d4e5f6",
  "title": "Apple plunged -7.35% today",
  "url": "https://finance.yahoo.com/quote/AAPL",
  "source": "stocks_movers",
  "category": "markets",
  "published": "2026-08-02T13:55:00Z",
  "heat": 93.0,
  "age_s": 3600,
  "tags": ["AAPL", "stocks"],
  "metrics": { "move_pct": -7.35, "price": 308.91 }
}
```

Categories: `tech · world · finance · crypto · markets · science · geohazard ·
weather · github · social · startups · video`

## How the pieces fit

| Layer | Files | Notes |
|---|---|---|
| Sensors | `collectors/*.py` | Python stdlib only, no `pip install`, ~3–30s each |
| Harness | `collectors/common.py` | fetch, retries, item schema, heat scoring |
| Orchestration | `.github/workflows/radar.yml` | 20-job matrix → aggregate → commit → deploy |
| Data store | `data/` | committed every sweep; snapshots + latest + history |
| Dashboard | `site/` | zero-build HTML/CSS/JS, refreshes every 5 min |
| Local dev | `scripts/run_all.py` | full sweep on your machine |

Heat = source score (log-scaled engagement) + recency boost (<30m +15, <2h +8).
Items ≥ 70 heat are flagged `BREAKING`. Deduplication is title-normalized.

## Adding a sensor (5 lines)

```python
# collectors/mysource.py
from common import item, main

def collect(runner_id):
    return [item(runner_id, "world", "Something broke", "https://...", score=80)]

if __name__ == "__main__":
    main("my_runner", collect, args=["my_runner"])
```

Then add one line to the matrix in `radar.yml` and one to `RUNNERS` in
`scripts/run_all.py`. That's it — dashboard, data store, and API pick it up
automatically.

## Cost & operations

- **$0 infra**: GitHub Actions (public repo) + GitHub Pages + free data providers.
- Sweep every 2h = 12 sweeps/day ≈ 240 job-minutes/day (well under limits).
- Contributors to data providers: Hacker News API, Reddit JSON, GitHub trending,
  RSS feeds, CoinGecko, Yahoo Finance spark, USGS GeoJSON, NWS API.

## Monetization path

The hard part (data pipeline, history, API) is already built. For the paid
product:

1. **Sell API access** — `all.json`/`history.json` are the product. Wrap them
   with a keyed proxy (e.g. Supabase Edge Functions) and bill $50–200/mo per
   trader/agency subscriber (Stripe). Add webhooks for `heat ≥ 80` events.
2. **Differentiated tiers** — free tier: 4h latency; paid: push alerts, full
   history, custom categories, sector filters.
3. **B2B angles** — creator dashboards, alt-news monitoring for hedge funds,
   regional trend packages for newsrooms.

## Roadmap

- [ ] Webhook/email alerts on BREAKING events (Supabase + Edge Functions)
- [ ] LLM summarization of the top-10 events per sweep
- [ ] More sensors: Google Trends, DXY/FX moves, satellite anomaly feeds (GDACS), Meme/stock correlation scoring
- [ ] Subscriber tiering + API keys via Supabase
- [ ] Telegram/Discord bot pushing the ticker

---

**License:** MIT. Data sources remain property of their respective providers —
review each provider's terms before reselling data commercially.
