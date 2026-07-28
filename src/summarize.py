import json
import os
import sys

from dotenv import load_dotenv
from groq import Groq

from discover import discover_articles, load_categories
from embed import rank_articles
from scrape import scrape_articles

load_dotenv()

MODEL = "openai/gpt-oss-120b"
TEXT_TRUNCATE_CHARS = 3000

SYSTEM_PROMPT = (
    "You are a news digest assistant. Given an article, produce a 2-3 "
    "sentence summary and a 1-2 sentence explanation of why it matters to "
    "someone who follows this topic."
)

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "article_summary",
        "schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "why_it_matters": {"type": "string"},
            },
            "required": ["summary", "why_it_matters"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


def get_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


def summarize_article(client, article):
    user_prompt = (
        f"Title: {article['title']}\n"
        f"Category: {article['category']}\n"
        f"Article text:\n{article['text'][:TEXT_TRUNCATE_CHARS]}"
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format=RESPONSE_SCHEMA,
        temperature=0.3,
    )

    parsed = json.loads(response.choices[0].message.content)

    return {
        **article,
        "summary": parsed["summary"],
        "why_it_matters": parsed["why_it_matters"],
    }


def summarize_ranked(ranked):
    client = get_client()
    summarized = {}

    for category_name, articles in ranked.items():
        summarized_articles = []
        for article in articles:
            try:
                summarized_articles.append(summarize_article(client, article))
            except Exception as e:
                print(f"  skipped '{article['title']}': {e}")
        summarized[category_name] = summarized_articles

    return summarized


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    categories = load_categories()
    found = discover_articles()
    scraped = scrape_articles(found)
    ranked = rank_articles(scraped, categories)

    print(f"Summarizing top articles across {len(ranked)} categories...\n")
    summarized = summarize_ranked(ranked)

    for category_name, articles in summarized.items():
        print(f"== {category_name} ==")
        for article in articles:
            print(f"- {article['title']}")
            print(f"  Summary: {article['summary']}")
            print(f"  Why it matters: {article['why_it_matters']}\n")
