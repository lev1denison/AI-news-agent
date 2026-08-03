# AI News Agent

A personal, automated news digest. It searches for articles matching your
interests, scrapes the full text, ranks each article by relevance using
local embeddings, summarizes the relevant ones with a free-tier LLM, and
emails you the result daily.

## How it works

1. **Discover** (`src/discover.py`): searches Tavily for each configured
   interest query, grouped into categories, and deduplicates results by URL.
2. **Scrape** (`src/scrape.py`): fetches and extracts full article text with
   Trafilatura, filtering out non-article pages (ticker quote pages,
   navigation/error pages, pages with too little text).
3. **Embed and Rank** (`src/embed.py`): embeds article text with
   sentence-transformers, stores it in a local Chroma vector store, and
   ranks articles within each category by cosine similarity to that
   category's interest profile.
4. **Summarize** (`src/summarize.py`): sends the top-ranked articles per
   category to a free-tier LLM (Groq) to generate a summary and a short
   explanation of why the article matters.
5. **Deliver** (`src/deliver.py`): emails the finished digest using Resend.
6. **Orchestrate** (`src/main.py`): runs the full pipeline end to end.

A later phase adds a feedback loop: thumbs up or down on articles, stored in
`data/feedback.json`, used to train a scikit-learn ranking model
(`src/rank.py`) that improves relevance over time.

## Project structure

```
config/interests.json      categories and search queries
data/feedback.json         user feedback for the ranking model (later phase)
src/discover.py            Tavily search
src/scrape.py              Trafilatura scraping and filtering
src/embed.py               embeddings and Chroma ranking
src/rank.py                ML ranking model (later phase)
src/summarize.py           LLM summarization
src/deliver.py             Resend email delivery
src/main.py                pipeline orchestration
.github/workflows/         scheduled daily run (later phase)
```

## Setup

1. Create and activate a virtual environment:

   ```
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your API keys:

   ```
   TAVILY_API_KEY=your_key_here
   GROQ_API_KEY=your_key_here
   RESEND_API_KEY=your_key_here
   FROM_EMAIL=your_sender_address
   TO_EMAIL=your_recipient_address
   ```

   Until you verify your own domain in Resend, `FROM_EMAIL` must be the
   shared test sender (`onboarding@resend.dev`) and `TO_EMAIL` must match
   the email address on your Resend account.

4. Edit `config/interests.json` to set your own categories and search
   queries.

## Configuration

`config/interests.json` defines the categories the digest is organized
into. Each category has a name, a Tavily search topic (`news` or
`finance`), and a list of search queries:

```json
{
  "categories": [
    {
      "name": "AI & LLM News",
      "topic": "news",
      "queries": ["AI agent news today", "large language model updates today"]
    }
  ]
}
```

## Running individual stages

Each module can be run on its own for testing:

```
python src/discover.py     # print discovered articles by category
python src/scrape.py       # discover, then scrape and print article text
python src/embed.py        # discover, scrape, then rank by relevance
python src/summarize.py    # discover, scrape, rank, then summarize top articles
python src/deliver.py      # run the full pipeline and send the digest email
python src/main.py         # same as deliver.py, with stage-by-stage logging
```

## Status

The full pipeline (discover, scrape, embed/rank, summarize, deliver, main)
is implemented and has been run end to end against live APIs, including
sending a real digest email.

Remaining for phase 1:

- `.github/workflows/daily_digest.yml`, to run the pipeline on a schedule.
  This should also cache the Hugging Face model directory so the
  embedding model isn't re-downloaded on every run.
- Verifying a domain in Resend, so the digest can be sent to a real
  recipient address instead of the Resend account owner's email (a
  restriction of the shared test sender).
- Optional: recency-weighted ranking. `embed.py` currently ranks purely
  by semantic similarity; Tavily's `published_date` per article isn't
  yet captured or used as a ranking signal.

Phase 2 (feedback loop and `rank.py`) has not been started.

## Notes

- The Chroma vector store persists to `chroma_db/`, which is not committed
  to git and is rebuilt on every run.
- The embedding model is downloaded from Hugging Face on first use and
  cached locally afterward.
- `.env`, `venv/`, and `chroma_db/` are excluded from git via `.gitignore`.
