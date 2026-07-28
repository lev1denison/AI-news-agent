import sys
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
        profile_text = name + ": " + "; ".join(category["queries"])
        query_embedding = model.encode([profile_text])[0].tolist()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, len(scraped)),
            where={"category": name},
        )

        category_articles = []
        for id_str, distance in zip(results["ids"][0], results["distances"][0]):
            article = dict(scraped[int(id_str)])
            article["score"] = 1 - distance
            category_articles.append(article)

        ranked[name] = category_articles

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
            print(f"  [{article['score']:.3f}] {article['title']}")
        print()
