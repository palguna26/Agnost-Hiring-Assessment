# Architecture

I kept the system deliberately small. A client sends an Agnost SDK-shaped conversation to the API, the API stores it, a worker analyzes it, and the query endpoints read the resulting topics and trend snapshots. That means the user-facing side stays simple, and the analysis can evolve underneath it without changing the contract.

## What the system is made of

- FastAPI handles the public endpoints: `/health`, `/ingest`, `/topics`, `/topics/{topic_id}`, `/trends`, and `/alerts`.
- PostgreSQL stores the durable data: raw conversations, topic records, and bucketed trend snapshots.
- The worker picks up pending conversations, turns the user side of each conversation into embeddings, scores sentiment, clusters related requests, and writes the topic/trend updates.
- A small sample-data generator makes it easy to replay realistic conversations locally.

## How the data moves

1. A client posts a session payload to `/ingest`.
2. The API validates it and stores the raw conversation with `analysis_status="pending"`.
3. The worker reads pending rows, extracts the user-authored text, computes embeddings, and groups similar conversations together.
4. The worker scores sentiment, updates the topic summary, and writes a trend snapshot for the current time bucket.
5. The query endpoints read the saved rows and return PM-friendly JSON instead of raw model output.

## What each query returns

- `/topics` gives a ranked list of topics in an `{"items": [...]}` envelope.
- `/topics/{topic_id}` gives the topic summary, keywords, sentiment mix, representative conversations, and trend curve.
- `/trends` gives bucketed topic movement in an `{"items": [...]}` envelope.
- `/alerts` gives the topics that cross the growth, negativity, and severity thresholds.

## Why it stays this small

The point of the prototype is to prove the loop from raw conversation to useful PM insight. One database, one API process, and one worker are enough to do that clearly. I did not add a queue, a separate vector store, or a dashboard because those would make the local setup harder without improving the core demo very much.

If this were a longer project, I would split out more infrastructure later. For this submission, the simplest working shape is the right one.
