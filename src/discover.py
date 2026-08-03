import json
import os
from pathlib import Path

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

INTERESTS_PATH = Path(__file__).resolve().parent.parent / "config" / "interests.json"

RESULTS_PER_QUERY = 5
RECENCY_DAYS = 1


def load_categories():
    with open(INTERESTS_PATH, encoding="utf-8") as f:
        config = json.load(f)
    return config["categories"]


def discover_articles():
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    categories = load_categories()

    seen_urls = set()
    articles = []

    for category in categories:
        topic = category.get("topic", "news")
        for query in category["queries"]:
            response = client.search(
                query=query,
                topic=topic,
                days=RECENCY_DAYS,
                max_results=RESULTS_PER_QUERY,
            )

            for result in response.get("results", []):
                url = result.get("url")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                articles.append(
                    {
                        "category": category["name"],
                        "query": query,
                        "title": result.get("title"),
                        "url": url,
                        "snippet": result.get("content"),
                        "published_date": result.get("published_date"),
                    }
                )

    return articles


if __name__ == "__main__":
    found = discover_articles()
    print(f"Found {len(found)} unique articles\n")

    by_category = {}
    for article in found:
        by_category.setdefault(article["category"], []).append(article)

    for category_name, items in by_category.items():
        print(f"== {category_name} ({len(items)}) ==")
        for item in items:
            print(f"- {item['title']}\n  {item['url']}")
        print()
