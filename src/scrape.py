import re
import sys

import trafilatura

from discover import discover_articles

MIN_TEXT_LENGTH = 300

BOILERPLATE_MARKERS = [
    "skip to navigation",
    "skip to main content",
    "something went wrong",
]

NON_ARTICLE_URL_PATTERNS = [
    r"^https?://[^/]+/?$",
    r"/history$",
    r"/community$",
    r"/quote/[^/]+$",
    r"/quote/[^/]+/$",
    r"/calendar(/|$|\?)",
    r"/key-statistics$",
]


def is_likely_article(url):
    return not any(re.search(pattern, url) for pattern in NON_ARTICLE_URL_PATTERNS)


def is_boilerplate(text):
    lowered = text.lower()
    return any(marker in lowered for marker in BOILERPLATE_MARKERS)


def scrape_article(article):
    downloaded = trafilatura.fetch_url(article["url"])
    if not downloaded:
        return None

    text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    if not text or len(text) < MIN_TEXT_LENGTH:
        return None

    if is_boilerplate(text):
        return None

    result = {**article, "text": text}

    metadata = trafilatura.extract_metadata(downloaded)
    if metadata and metadata.date:
        result["published_date"] = metadata.date

    return result


def scrape_articles(articles):
    scraped = []
    for article in articles:
        if not is_likely_article(article["url"]):
            continue

        result = scrape_article(article)
        if result:
            scraped.append(result)

    return scraped


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    found = discover_articles()
    print(f"Discovered {len(found)} articles, scraping...\n")

    scraped = scrape_articles(found)
    print(f"Scraped {len(scraped)}/{len(found)} articles successfully\n")

    for article in scraped:
        print(f"== {article['title']} ({article['category']}) ==")
        print(f"{article['text'][:200]}...\n")
