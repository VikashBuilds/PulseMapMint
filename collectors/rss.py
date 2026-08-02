"""RSS feed runner. Usage: rss.py <runner_id> <feed_group>"""

import json
import os
import sys
import xml.etree.ElementTree as ET

from common import fetch, item, main, now_iso

CONFIG = os.path.join(os.path.dirname(__file__), "..", "config", "rss_sources.json")

CATEGORY_MAP = {
    "rss_world": "world",
    "rss_tech": "tech",
    "rss_finance": "finance",
    "rss_science_space": "science",
}


def parse_feed(runner_id, category, raw):
    out = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return out
    if root.tag == "rss":
        entries = root.findall("./channel/item")
        feed_title_el = root.find("./channel/title")
    else:
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        feed_title_el = root.find("{http://www.w3.org/2005/Atom}title")
    feed_title = feed_title_el.text if feed_title_el is not None else runner_id
    for e in entries[:40]:
        title = None
        url = None
        published = None
        for child in e:
            tag = child.tag.split("}")[-1]
            if tag == "title" and title is None:
                title = child.text
            elif tag == "link":
                if child.tag.startswith("{"):
                    href = child.get("href")
                    if href:
                        url = href
                elif child.get("url"):
                    url = child.get("url")
                elif child.text:
                    url = child.text
            elif tag == "guid" and url is None and child.text:
                url = child.text
            elif tag == "pubDate":
                published = child.text
            elif tag == "updated" and published is None:
                published = child.text
        if not title or not url:
            continue
        out.append(
            item(
                runner_id,
                category,
                title,
                url,
                score=45,
                published=published,
                tags=[feed_title, "rss"],
                metrics={"feed": feed_title, "published_raw": published or ""},
            )
        )
    return out


def collect(runner_id, group):
    with open(CONFIG, encoding="utf-8") as fh:
        feeds = json.load(fh).get(group, [])
    category = CATEGORY_MAP.get(runner_id, "news")
    out = []
    for url in feeds:
        try:
            out.extend(parse_feed(runner_id, category, fetch(url, timeout=25)))
        except Exception:  # noqa: BLE001
            continue
    return out


if __name__ == "__main__":
    rid = sys.argv[1] if len(sys.argv) > 1 else "rss_world"
    main(rid, collect, args=[rid, rid])
