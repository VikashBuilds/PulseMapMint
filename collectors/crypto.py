"""Crypto anomaly runner. Usage: crypto.py <runner_id> [min_move_pct] [top_n]"""

import sys

from common import fetch_json, item, main

COINS_URL = (
    "https://api.coingecko.com/api/v3/coins/markets"
    "?vs_currency=usd&order=market_cap_desc&per_page=100"
    "&page=1&sparkline=false&price_change_percentage=1h,24h,7d"
)
WATCH_SYMBOLS = ["btc", "eth", "sol", "xrp", "doge", "ada", "avax", "link", "dot", "ltc"]


def collect(runner_id, min_move, top_n):
    min_move = float(min_move)
    top_n = int(top_n)
    coins = fetch_json(COINS_URL, timeout=40)
    watch = {}
    out = []
    for c in coins:
        sym = (c.get("symbol") or "").lower()
        if sym in WATCH_SYMBOLS:
            watch[sym] = {"price": c.get("current_price"), "pct24h": c.get("price_change_percentage_24h")}
        move24 = c.get("price_change_percentage_24h") or 0
        move = abs(move24)
        if move < min_move:
            continue
        score = min(95, 55 + move * 2.5)
        out.append(
            item(
                runner_id,
                "crypto",
                f"{c.get('name')} ({sym.upper()}) moved {move24:+.1f}% in 24h",
                f"https://www.coingecko.com/en/coins/{c.get('id')}",
                score=score,
                tags=[sym, "crypto"],
                metrics={
                    "symbol": sym,
                    "pct24h": round(c.get("price_change_percentage_24h") or 0, 2),
                    "pct1h": round(c.get("price_change_percentage_1h_in_currency") or 0, 2),
                    "pct7d": round(c.get("price_change_percentage_7d_in_currency") or 0, 2),
                    "price_usd": c.get("current_price"),
                    "market_cap": c.get("market_cap"),
                },
            )
        )
    out.sort(key=lambda x: -x["score"])
    return out[:top_n], {"watch": watch}


if __name__ == "__main__":
    rid = sys.argv[1] if len(sys.argv) > 1 else "crypto_anomalies"
    extra_args = sys.argv[2:] or ["4", "30"]
    main(rid, collect, args=[rid] + extra_args)
