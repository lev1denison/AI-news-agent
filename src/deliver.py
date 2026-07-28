import os
import sys
from html import escape

import resend
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY")


def require_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def build_html(summarized):
    sections = []
    for category_name, articles in summarized.items():
        if not articles:
            continue

        items = "".join(
            f"<li style='margin-bottom:16px;'>"
            f"<a href='{escape(article['url'])}'><strong>{escape(article['title'])}</strong></a><br>"
            f"{escape(article['summary'])}<br>"
            f"<em>Why it matters: {escape(article['why_it_matters'])}</em>"
            f"</li>"
            for article in articles
        )
        sections.append(
            f"<h2>{escape(category_name)}</h2><ul>{items}</ul>"
        )

    if not sections:
        sections.append("<p>No relevant articles found today.</p>")

    return f"<html><body>{''.join(sections)}</body></html>"


def build_text(summarized):
    lines = []
    for category_name, articles in summarized.items():
        if not articles:
            continue
        lines.append(category_name)
        lines.append("-" * len(category_name))
        for article in articles:
            lines.append(article["title"])
            lines.append(article["url"])
            lines.append(article["summary"])
            lines.append(f"Why it matters: {article['why_it_matters']}")
            lines.append("")
        lines.append("")

    if not lines:
        lines.append("No relevant articles found today.")

    return "\n".join(lines)


def send_digest(summarized, subject="Your daily news digest"):
    from_email = require_env("FROM_EMAIL")
    to_email = require_env("TO_EMAIL")

    params = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": build_html(summarized),
        "text": build_text(summarized),
    }

    return resend.Emails.send(params)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    from discover import discover_articles, load_categories
    from embed import rank_articles
    from scrape import scrape_articles
    from summarize import summarize_ranked

    categories = load_categories()
    found = discover_articles()
    scraped = scrape_articles(found)
    ranked = rank_articles(scraped, categories)
    summarized = summarize_ranked(ranked)

    result = send_digest(summarized)
    print(f"Sent: {result}")
