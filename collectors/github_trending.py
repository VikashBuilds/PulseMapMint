"""GitHub trending runner. Usage: github_trending.py <runner_id> [language] [language...]"""

import re
import sys

from common import fetch, item, main

BASE = "https://github.com/trending"
ARTICLE_RE = re.compile(r'<article class="Box-row">([\s\S]*?)</article>')
REPO_RE = re.compile(r'<a [^>]*href="(/[^"]+/[^"]+)"[^>]*class="Link"')
DESC_RE = re.compile(r'<p class="col-9 color-fg-muted[^"]*">\s*([\s\S]*?)\s*</p>')
STARS_TODAY_RE = re.compile(r"([\d,]+)\s+stars today")
LANG_RE = re.compile(r'itemprop="programmingLanguage">([^<]+)<')


def clean(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


def collect(runner_id, *languages):
    out = []
    for lang in languages or [None]:
        url = BASE + (f"/{lang}" if lang else "")
        html = fetch(url, timeout=30).decode("utf-8", "replace")
        for article in ARTICLE_RE.findall(html):
            m = REPO_RE.search(article)
            if not m:
                continue
            full = m.group(1).strip("/")
            if "/" not in full:
                continue
            owner, name = full.split("/", 1)
            gained_s = STARS_TODAY_RE.search(article)
            gained = int(gained_s.group(1).replace(",", "")) if gained_s else None
            desc_m = DESC_RE.search(article)
            desc = clean(desc_m.group(1)) if desc_m else ""
            lang_m = LANG_RE.search(article)
            prog_lang = lang_m.group(1).strip() if lang_m else None
            import math

            score = 25 if gained is None else min(95, 30 + math.log10(gained + 1) * 18)
            out.append(
                item(
                    runner_id,
                    "github",
                    f"{owner}/{name}",
                    f"https://github.com/{full}",
                    score=score,
                    published=None,
                    tags=[lang or "all-langs", "github-trending"],
                    metrics={
                        "stars_today": gained,
                        "language": prog_lang or lang or "all",
                        "description": desc[:200],
                        "topic": lang or "all",
                    },
                )
            )
    return out


if __name__ == "__main__":
    rid = sys.argv[1] if len(sys.argv) > 1 else "github_all"
    main(rid, collect, args=[rid] + (sys.argv[2:] or [None]))
