# Sentiment Analytics Engine

This is a small FastAPI prototype for turning Agnost SDK-style conversations into PM-friendly topic, trend, and alert views.

The idea is simple: a conversation comes in, the app stores it, the worker analyzes it, and the API serves the result in a form a product manager can actually read.

## Running it locally

1. Start PostgreSQL:

```bash
docker compose up -d
```

2. If you want to override the defaults, copy the example environment file:

```bash
Copy-Item .env.example .env
```

3. Apply the migration:

```bash
alembic upgrade head
```

4. Start the API:

```bash
uvicorn agnost_analytics.main:app --reload
```

5. Refresh the sample data if you want a local replay set:

```bash
python scripts/generate_sample_data.py
```

## What to hit

- `GET /health` checks that the app is up.
- `POST /ingest` accepts an Agnost SDK-shaped conversation payload.
- `GET /topics` returns the current topic list.
- `GET /topics/{topic_id}` returns one topic in more detail.
- `GET /trends` returns topic movement over time.
- `GET /alerts` returns the topics that look most urgent.

Interactive docs are available at `/docs` once the app is running.

## Sample data

The replayable sample data lives at `data/sample_conversations.jsonl`.

Regenerate it with:

```bash
python scripts/generate_sample_data.py --output data/sample_conversations.jsonl
```

## What this repo is trying to prove

This build is intentionally small. It shows that you can ingest raw conversations, cluster them into emerging themes, score sentiment, and surface something useful to PMs without building a huge platform first.

With more time, the next step would be a human review loop, better topic quality checks, and a more production-grade vector layer. But for now, the goal is to keep the system understandable and usable.
