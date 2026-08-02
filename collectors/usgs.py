"""USGS earthquake runner. Usage: usgs.py <runner_id> [min_mag]"""

import sys

from common import fetch_json, item, main

FEED = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"


def collect(runner_id, min_mag):
    min_mag = float(min_mag)
    data = fetch_json(FEED, timeout=40)
    out = []
    for f in data.get("features", []):
        p = f.get("properties", {})
        mag = p.get("mag") or 0
        if mag < min_mag:
            continue
        geom = f.get("geometry", {})
        lon, lat = geom.get("coordinates", [0, 0])[:2]
        place = p.get("place") or "Unknown location"
        score = min(99, 40 + mag * 8)
        out.append(
            item(
                runner_id,
                "geohazard",
                f"M{mag} earthquake — {place}",
                p.get("url") or f"https://earthquake.usgs.gov/earthquakes/map/",
                score=score,
                published=(p.get("time") or 0) / 1000,
                tags=["earthquake", "usgs"],
                metrics={
                    "mag": mag,
                    "depth_km": round((geom.get("coordinates") or [0, 0, 0])[2], 1),
                    "lat": round(lat, 3),
                    "lon": round(lon, 3),
                    "tsunami": bool(p.get("tsunami")),
                    "status": p.get("status"),
                },
            )
        )
    out.sort(key=lambda x: -x["score"])
    return out


if __name__ == "__main__":
    rid = sys.argv[1] if len(sys.argv) > 1 else "usgs_quakes"
    main(rid, collect, args=[rid] + (sys.argv[2:] or ["4.0"]))
