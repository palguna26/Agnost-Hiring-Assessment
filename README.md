# Sentiment Analytics Engine

Small FastAPI prototype for ingesting Agnost SDK-style conversations, clustering them into topics, and serving PM-facing topic, trend, and alert views.

## Local run

1. Start PostgreSQL:

```bash
docker compose up -d
```

2. Create a `.env` file from the example if you want to override the defaults:

```bash
Copy-Item .env.example .env
```

3. Apply the database migration:

```bash
alembic upgrade head
```

4. Start the API:

```bash
uvicorn agnost_analytics.main:app --reload
```

5. Generate or refresh the sample data:

```bash
python scripts/generate_sample_data.py
```

## API endpoints

- `GET /health` returns `{"status":"ok"}`
- `POST /ingest` accepts an Agnost SDK-shaped conversation payload
- `GET /topics` lists topics as `{"items":[...]}`
- `GET /topics/{topic_id}` returns one topic with detail fields
- `GET /trends` lists trend snapshots as `{"items":[...]}`
- `GET /alerts` lists high-severity topics as `{"items":[...]}`

Interactive docs are available at `/docs` once the app is running.

## Sample data

The sample conversations file lives at `data/sample_conversations.jsonl`. Regenerate it with:

```bash
python scripts/generate_sample_data.py --output data/sample_conversations.jsonl
```
