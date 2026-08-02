"""NWS active weather alerts runner (US, free, no key).
Usage: weather.py <runner_id> [min_severity]"""

import sys

from common import fetch_json, item, main

NWS_URL = "https://api.weather.gov/alerts/active"
SEVERITY_SCORE = {"Extreme": 92, "Severe": 75, "Moderate": 60, "Minor": 45, "Unknown": 40}


def collect(runner_id, min_severity):
    min_score = SEVERITY_SCORE.get(min_severity.title(), 60)
    data = fetch_json(NWS_URL, headers={"Accept": "application/geo+json"}, timeout=40)
    out = []
    for f in data.get("features", []):
        p = f.get("properties", {})
        sev = p.get("severity") or "Unknown"
        score = SEVERITY_SCORE.get(sev, 40)
        if score < min_score:
            continue
        event = p.get("event") or "Weather alert"
        area = (p.get("areaDesc") or "").split(";")[0].strip() or "region"
        headline = (p.get("headline") or f"{event} — {area}")[:240]
        out.append(
            item(
                runner_id,
                "weather",
                headline,
                p.get("id") or "https://www.weather.gov/",
                score=score,
                published=p.get("sent"),
                tags=["nws", sev.lower(), "alert"],
                metrics={
                    "severity": sev,
                    "event": event,
                    "area": area,
                    "sender": p.get("senderName"),
                    "expires": p.get("expires"),
                    "description": (p.get("description") or "")[:200],
                },
            )
        )
    out.sort(key=lambda x: -x["score"])
    return out


if __name__ == "__main__":
    rid = sys.argv[1] if len(sys.argv) > 1 else "weather_alerts"
    main(rid, collect, args=[rid] + (sys.argv[2:] or ["Severe"]))
