"""Shared harness for all PulseMap collectors. Stdlib only."""

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import datetime

USER_AGENT = "PulseMapRadar/1.0 (+https://github.com/pulsemap/radar)"
OUT_DIR = os.environ.get("PULSEMAP_OUT", "out")


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_json(url, headers=None, timeout=30):
    return json.loads(fetch(url, headers=headers, timeout=timeout).decode("utf-8", "replace"))


def fetch(url, headers=None, timeout=30):
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "*/*", **(headers or {})}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} for {url}") from e


def fetch_many(urls, headers=None, timeout=25, max_workers=10):
    results = {}
    failures = {}
    import concurrent.futures as cf

    with cf.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = {pool.submit(fetch_json, u, headers, timeout): u for u in urls}
        for fut in cf.as_completed(futs):
            u = futs[fut]
            try:
                results[u] = fut.result()
            except Exception as e:  # noqa: BLE001
                failures[u] = str(e)
    return results, failures


def parse_dt(value):
    if not value:
        return now_iso()
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, AttributeError):
        pass
    try:
        import email.utils

        dt = email.utils.parsedate_to_datetime(str(value).strip())
        if dt:
            return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError, OverflowError):
        pass
    return now_iso()


def item(runner, category, title, url, score=50, published=None, tags=None, metrics=None):
    key = re.sub(r"[^a-z0-9]", "", (title or "").lower())[:80] or url
    return {
        "id": hashlib.md5(f"{key}|{url}".encode("utf-8")).hexdigest()[:12],
        "title": re.sub(r"\s+", " ", (title or "").strip())[:240],
        "url": url or "",
        "source": runner,
        "category": category,
        "published": parse_dt(published),
        "score": min(100.0, max(0.0, float(score))),
        "tags": tags or [],
        "metrics": metrics or {},
    }


def heat_from_log(value, base=25, scale=25):
    if value <= 0:
        return 0
    return base + scale * min(3.0, (value ** 0.5) / 10)


def run(runner_id, fn, args=None, extra=None):
    started = time.time()
    try:
        result = fn(*(args or []))
        if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], dict):
            items, extra = result
        else:
            items = result or []
        status = "ok" if items else "empty"
        error = None
    except Exception as e:  # noqa: BLE001
        items, status, error = [], "error", f"{type(e).__name__}: {e}"
    payload = {
        "runner": runner_id,
        "generated": now_iso(),
        "status": status,
        "error": error,
        "took_s": round(time.time() - started, 2),
        "args": args or [],
        "items": items,
    }
    if extra:
        payload.update(extra)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{runner_id}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print(f"[{runner_id}] {status} items={len(items)} took={payload['took_s']}s")
    return path


def main(runner_id, fn, needs_key=None, args=None):
    args = args if args is not None else sys.argv[1:]
    if needs_key and not os.environ.get(needs_key):
        payload = {
            "runner": runner_id,
            "generated": now_iso(),
            "status": "skipped",
            "error": f"missing env var {needs_key}",
            "took_s": 0.0,
            "args": args,
            "items": [],
        }
        os.makedirs(OUT_DIR, exist_ok=True)
        path = os.path.join(OUT_DIR, f"{runner_id}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
        print(f"[{runner_id}] skipped (needs {needs_key})")
        return path
    return run(runner_id, fn, args=args)
