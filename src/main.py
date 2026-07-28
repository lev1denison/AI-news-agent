import sys

from deliver import send_digest
from discover import discover_articles, load_categories
from embed import rank_articles
from scrape import scrape_articles
from summarize import summarize_ranked


def run():
    categories = load_categories()

    print("Discovering articles...")
    found = discover_articles()
    print(f"  found {len(found)} unique articles")

    print("Scraping articles...")
    scraped = scrape_articles(found)
    print(f"  scraped {len(scraped)} articles")

    print("Ranking articles...")
    ranked = rank_articles(scraped, categories)
    for category_name, articles in ranked.items():
        print(f"  {category_name}: {len(articles)} candidates")

    print("Summarizing articles...")
    summarized = summarize_ranked(ranked)
    for category_name, articles in summarized.items():
        print(f"  {category_name}: {len(articles)} summarized")

    print("Sending digest...")
    result = send_digest(summarized)
    print(f"  sent: {result}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    run()
