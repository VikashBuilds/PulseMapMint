"""Stock mover runner (Yahoo Finance spark, free, no key).
Usage: stocks.py <runner_id> [min_move_pct]"""

import concurrent.futures as cf
import json
import os
import sys

from common import fetch_json, item, main

CONFIG = os.path.join(os.path.dirname(__file__), "..", "config", "stocks.json")
SPARK = "https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=1d&interval=1d"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
MAX_PER_REQUEST = 20


def collect(runner_id, min_move):
    min_move = float(min_move)
    with open(CONFIG, encoding="utf-8") as fh:
        symbols = json.load(fh)
    keys = list(symbols.keys())
    chunks = [keys[i : i + MAX_PER_REQUEST] for i in range(0, len(keys), MAX_PER_REQUEST)]

    def one(chunk):
        query = ",".join(chunk)
        return fetch_json(SPARK.format(symbols=query), headers=HEADERS, timeout=45)

    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(one, chunks))

    out = []
    for data in results:
        for r in data.get("spark", {}).get("result", []):
            sym = r.get("symbol", "").upper()
            name = symbols.get(sym, sym)
            resp = (r.get("response") or [None])[0]
            if not resp:
                continue
            meta = resp.get("meta", {})
            price = meta.get("regularMarketPrice")
            prev = meta.get("chartPreviousClose")
            if not price or not prev:
                continue
            move = (price - prev) / prev * 100
            if abs(move) < min_move:
                continue
            score = min(95, 55 + abs(move) * 6)
            direction = "surged" if move > 0 else "plunged"
            out.append(
                item(
                    runner_id,
                    "markets",
                    f"{name} {direction} {move:+.2f}% today",
                    f"https://finance.yahoo.com/quote/{sym}",
                    score=score,
                    tags=[sym, "stocks"],
                    metrics={
                        "symbol": sym,
                        "move_pct": round(move, 2),
                        "price": round(price, 2),
                        "prev_close": round(prev, 2),
                        "day_high": meta.get("regularMarketDayHigh"),
                        "day_low": meta.get("regularMarketDayLow"),
                        "volume": meta.get("regularMarketVolume"),
                    },
                )
            )
    out.sort(key=lambda x: -x["score"])
    return out


if __name__ == "__main__":
    rid = sys.argv[1] if len(sys.argv) > 1 else "stocks_movers"
    main(rid, collect, args=[rid] + (sys.argv[2:] or ["2.5"]))
