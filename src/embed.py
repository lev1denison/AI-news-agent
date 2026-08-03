import math
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from discover import discover_articles
from scrape import scrape_articles

MODEL_NAME = "all-MiniLM-L6-v2"
CHROMA_PATH = str(Path(__file__).resolve().parent.parent / "chroma_db")
COLLECTION_NAME = "articles"
TOP_K_PER_CATEGORY = 8
TEXT_TRUNCATE_CHARS = 2000

SIMILARITY_WEIGHT = 0.5
RECENCY_WEIGHT = 0.5
RECENCY_HALF_LIFE_HOURS = 6
DEFAULT_RECENCY_SCORE = 0.5


def parse_published_date(published_date):
    try:
        return parsedate_to_datetime(published_date)
    except (TypeError, ValueError, IndexError):
        pass

    try:
        return datetime.fromisoformat(published_date)
    except (TypeError, ValueError):
        return None


def normalize_tz(dt):
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def recency_score(published_date, reference_time):
    if not published_date:
        return DEFAULT_RECENCY_SCORE

    published = parse_published_date(published_date)
    if published is None:
        return DEFAULT_RECENCY_SCORE

    published = normalize_tz(published)
    age_hours = (reference_time - published).total_seconds() / 3600
    age_hours = max(age_hours, 0)

    return math.exp(-age_hours / RECENCY_HALF_LIFE_HOURS)

_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    return client.get_or_create_collection(
        COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def rank_articles(scraped, categories, top_k=TOP_K_PER_CATEGORY):
    if not scraped:
        return {}

    model = get_model()
    collection = get_collection()

    texts = [article["text"][:TEXT_TRUNCATE_CHARS] for article in scraped]
    embeddings = model.encode(texts, show_progress_bar=False).tolist()
    ids = [str(i) for i in range(len(scraped))]
    metadatas = [{"category": article["category"]} for article in scraped]

    collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=texts)

    ranked = {}
    for category in categories:
        name = category["name"]
        category_items = [a for a in scraped if a["category"] == name]
        if not category_items:
            ranked[name] = []
            continue

        parsed_dates = [
            normalize_tz(parse_published_date(a.get("published_date")))
            for a in category_items
            if parse_published_date(a.get("published_date"))
        ]
        reference_time = max(parsed_dates) if parsed_dates else datetime.now(timezone.utc)

        profile_text = name + ": " + "; ".join(category["queries"])
        query_embedding = model.encode([profile_text])[0].tolist()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=len(category_items),
            where={"category": name},
        )

        category_articles = []
        for id_str, distance in zip(results["ids"][0], results["distances"][0]):
            article = dict(scraped[int(id_str)])
            similarity = 1 - distance
            recency = recency_score(article.get("published_date"), reference_time)
            article["similarity"] = similarity
            article["recency"] = recency
            article["score"] = (
                SIMILARITY_WEIGHT * similarity + RECENCY_WEIGHT * recency
            )
            category_articles.append(article)

        category_articles.sort(key=lambda a: a["score"], reverse=True)
        ranked[name] = category_articles[:top_k]

    return ranked


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    from discover import load_categories

    categories = load_categories()
    found = discover_articles()
    scraped = scrape_articles(found)
    print(f"Scraped {len(scraped)} articles, ranking...\n")

    ranked = rank_articles(scraped, categories)

    for category_name, articles in ranked.items():
        print(f"== {category_name} ==")
        for article in articles:
            print(
                f"  [score {article['score']:.3f} | sim {article['similarity']:.3f} "
                f"| recency {article['recency']:.3f}] {article['title']}"
            )
        print()
