"""
Pulls candidate articles for the day from two sources:
  1. RSS feeds — major wire services, defense/natsec trade press, and a
     couple of smaller outlets that often catch things bigger feeds miss.
  2. Topic search — reuses a plain-requests HTML scrape of DuckDuckGo and
     Bing (no API key), same approach proven out in the intel-research-bot
     project, to catch coverage outside the fixed feed list entirely.

Output: a flat list of raw article dicts. Deduplication/corroboration
across sources happens in corroborate.py, not here.
"""
import time
import feedparser
import requests
import trafilatura

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
FETCH_TIMEOUT = 10

# Major wire services / general news
GENERAL_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.reuters.com/world/rss",
    "https://rss.apnews.com/rss/apf-topnews",
    "https://www.aljazeera.com/xml/rss/all.xml",
]

# Defense / national security / cyber trade press — smaller audience,
# often first to report on things general wire services pick up later
DEFENSE_NATSEC_FEEDS = [
    "https://www.defensenews.com/arc/outboundfeeds/rss/",
    "https://breakingdefense.com/feed/",
    "https://therecord.media/feed",
    "https://krebsonsecurity.com/feed/",
    "https://www.bleepingcomputer.com/feed/",
    "https://www.darkreading.com/rss.xml",
]

# Smaller/regional outlets — worth including because local reporters
# sometimes catch a lead national/international coverage misses entirely
LOCAL_REGIONAL_FEEDS = [
    "https://www.stripes.com/rss",
]

ALL_FEEDS = GENERAL_FEEDS + DEFENSE_NATSEC_FEEDS + LOCAL_REGIONAL_FEEDS


def _fetch_article_text(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
        return trafilatura.extract(resp.text) or ""
    except Exception:
        return ""


def pull_from_feeds(max_per_feed: int = 8):
    articles = []
    for feed_url in ALL_FEEDS:
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=FETCH_TIMEOUT)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            source_name = parsed.feed.get("title", feed_url)
            for entry in parsed.entries[:max_per_feed]:
                url = entry.get("link")
                if not url:
                    continue
                articles.append({
                    "title": entry.get("title", "").strip(),
                    "url": url,
                    "source": source_name,
                    "published": entry.get("published", ""),
                    "snippet": entry.get("summary", ""),
                })
        except Exception:
            continue  # one bad feed shouldn't stop the rest
    return articles


def pull_from_topic_search(topics, max_results_per_topic: int = 5):
    """Reuses the same plain-requests DuckDuckGo/Bing scrape approach from
    intel-research-bot's websearch.py, kept self-contained here so this
    project has no dependency on that one."""
    from lxml import html as lxml_html
    from urllib.parse import urlparse, parse_qs, unquote
    import base64

    def _resolve_ddg(url):
        if "duckduckgo.com/l/" not in url:
            return url
        if url.startswith("//"):
            url = "https:" + url
        qs = parse_qs(urlparse(url).query)
        real = qs.get("uddg", [None])[0]
        return unquote(real) if real else url

    def _resolve_bing(url):
        if not url or "bing.com/ck/a" not in url:
            return url
        qs = parse_qs(urlparse(url).query)
        u = qs.get("u", [None])[0]
        if not u or not u.startswith("a1"):
            return url
        b64 = u[2:]
        b64 += "=" * (-len(b64) % 4)
        try:
            return base64.urlsafe_b64decode(b64).decode("utf-8", errors="ignore")
        except Exception:
            return url

    results = []
    for topic in topics:
        try:
            resp = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": topic}, headers=HEADERS, timeout=FETCH_TIMEOUT,
            )
            tree = lxml_html.fromstring(resp.text)
            for node in tree.xpath('//div[contains(@class,"result__body")]')[:max_results_per_topic]:
                a = node.xpath('.//a[contains(@class,"result__a")]')
                if not a:
                    continue
                title = a[0].text_content().strip()
                url = _resolve_ddg(a[0].get("href"))
                if "duckduckgo.com" in url:
                    continue
                snippet_el = node.xpath('.//a[contains(@class,"result__snippet")] | .//div[contains(@class,"result__snippet")]')
                snippet = snippet_el[0].text_content().strip() if snippet_el else ""
                if title and url:
                    results.append({"title": title, "url": url, "source": "web search", "published": "", "snippet": snippet})
        except Exception:
            pass

        try:
            resp = requests.get(
                "https://www.bing.com/search",
                params={"q": topic}, headers=HEADERS, timeout=FETCH_TIMEOUT,
            )
            tree = lxml_html.fromstring(resp.text)
            for node in tree.xpath('//li[contains(@class,"b_algo")]')[:max_results_per_topic]:
                a = node.xpath('.//h2/a')
                if not a:
                    continue
                title = a[0].text_content().strip()
                url = _resolve_bing(a[0].get("href"))
                snippet_el = node.xpath('.//p')
                snippet = snippet_el[0].text_content().strip() if snippet_el else ""
                if title and url:
                    results.append({"title": title, "url": url, "source": "web search", "published": "", "snippet": snippet})
        except Exception:
            pass

        time.sleep(1)  # be polite between topic queries
    return results


def dedupe_by_url(articles):
    seen = set()
    out = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            out.append(a)
    return out


def pull_all(topics):
    articles = pull_from_feeds()
    articles += pull_from_topic_search(topics)
    articles = dedupe_by_url(articles)

    # Attach full text where we can get it; snippet-only otherwise
    for a in articles:
        full_text = _fetch_article_text(a["url"])
        a["full_text"] = full_text
        a["full_text_extracted"] = bool(full_text)
        time.sleep(0.3)  # be polite to sources

    return articles
