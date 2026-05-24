# Sentiment Analytics Engine Design

## Goal

Build a weekend-scale prototype that ingests Agnost SDK conversation logs, discovers emerging topics, scores sentiment, and exposes PM-friendly analytics through a small HTTP API.

The system should answer questions like:

- Which negative topics are growing fastest right now?
- What conversations support a topic classification?
- How is sentiment shifting across the newest emerging issues?

The prototype will optimize for PM insight quality first, then demo clarity, then scalability realism.

## Scope

### In scope

- Near-real-time ingestion from an Agnost SDK-shaped payload
- Conversation normalization into a canonical session model
- Sentence-embedding-based topic discovery
- Density clustering for emerging topics
- Per-conversation sentiment scoring and per-topic sentiment aggregation
- Trend snapshots and alert generation
- API endpoints for topic browsing, topic detail, trends, and alerts

### Out of scope

- Full dashboard UI
- Human-in-the-loop topic moderation
- Cross-account multi-tenant access control
- Deep causal attribution or root-cause explanation beyond sample conversations and trend signals

## Assumed Input Schema

The prototype accepts a session-oriented payload that is easy to mock but compatible with a streaming integration later.

```json
{
  "session_id": "sess_123",
  "user_id": "user_456",
  "timestamp": "2026-05-24T10:15:00Z",
  "source": "agnost_sdk",
  "messages": [
    {"role": "user", "content": "Why was I charged twice?"},
    {"role": "assistant", "content": "Let me check that for you."}
  ],
  "metadata": {
    "app_id": "app_001",
    "channel": "chat",
    "tags": ["billing", "refund"]
  }
}
```

This shape keeps the prototype simple while still supporting later conversion from message-level streams into sessions.

## Architecture

The system uses one Postgres instance as the durable store and three logical storage layers inside it or attached to it:

- Relational layer for raw sessions, topic assignments, topic summaries, and API-facing metadata
- Vector layer for semantic similarity and cluster evolution support
- Time-series layer for trend snapshots and growth queries

The processing path is:

1. `POST /ingest` receives Agnost SDK-shaped session data.
2. The ingest handler validates and persists the raw session immediately.
3. A background worker picks up unprocessed sessions.
4. The worker computes embeddings, sentiment, and cluster membership.
5. The worker updates topic summaries and writes trend snapshots.
6. The API serves topic and trend views from persisted aggregates.

## Component Design

### Ingestion Service

Responsibility:

- Validate session payloads
- Store raw sessions durably
- Mark sessions as pending analysis

Dependencies:

- FastAPI
- PostgreSQL

Why this shape:

- It is realistic for an SDK-driven integration.
- It keeps ingestion cheap and resilient.
- It allows reprocessing if downstream analysis fails.

### Processing Worker

Responsibility:

- Compute sentence embeddings for each conversation
- Score sentiment as positive, negative, or neutral
- Assign conversations to an emerging topic cluster
- Update topic summaries, sample conversations, and trend snapshots

Dependencies:

- Embedding model
- Sentiment model
- Clustering algorithm
- Vector index
- PostgreSQL

Why this shape:

- It isolates model logic from serving logic.
- It supports retryable, idempotent processing.
- It lets the clustering algorithm evolve without changing the API contract.

### API Layer

Responsibility:

- Serve PM-facing topic and trend queries
- Expose alert-ranked emerging issues

Dependencies:

- PostgreSQL
- Optional vector lookups for similar conversations

Why this shape:

- It keeps the user-facing interface stable.
- It returns summaries instead of raw model internals.

## Database Choices

### PostgreSQL as the canonical store

Use Postgres for raw conversations, topic assignments, summaries, and API-visible metadata.

Why:

- Strong fit for relational session and topic data
- Simple weekend deployment
- Easy to query and inspect during debugging
- Good enough for the expected prototype scale

### Vector layer with FAISS or pgvector

Use FAISS in-process for the weekend prototype, or `pgvector` if the implementation wants everything in one database.

Why:

- Embeddings are required for semantic clustering and topic evolution
- FAISS keeps the prototype lightweight and avoids another service
- `pgvector` is the cleaner production path if the project wants a single-database deployment

Rejected alternatives:

- Pinecone/Qdrant: too much operational overhead for the weekend scope
- Pure keyword grouping: too brittle for emerging topics with varied language

### Time-series layer with Timescale-style hypertable or materialized aggregates

Use a time-bucketed table for topic counts and sentiment averages, either via TimescaleDB if enabled or plain Postgres materialized aggregates if not.

Why:

- Trend queries are central to the PM workflow
- Time-bucketed storage keeps alert and growth queries cheap

Rejected alternatives:

- Separate analytics database: unnecessary for the prototype
- Raw scans over session rows: too slow and noisy for trend queries

## Clustering and Sentiment Approach

### Topic discovery

Use sentence embeddings plus density clustering, specifically a MiniLM-style embedding model with HDBSCAN.

Why this choice:

- It finds groups by semantic similarity rather than exact wording
- It can leave outliers unclustered until enough similar sessions arrive
- It is strong for emerging topic discovery, which is the main PM need

Why not simpler keyword rules:

- Keyword matching misses paraphrases and thinly repeated complaints
- It struggles with new issue names that share meaning but not vocabulary

Why not LLM-only clustering:

- Too expensive and less deterministic for a streaming prototype
- Harder to explain and replay in a weekend build

### Topic labeling

Use a lightweight LLM only after clusters form, to generate human-readable topic names and short summaries.

This keeps discovery deterministic while still making the PM-facing output readable.

### Sentiment scoring

Use a pre-trained sentiment classifier to label each conversation as positive, negative, or neutral.

The prototype should aggregate sentiment at the topic level as:

- share of negative conversations
- average sentiment score
- trend in negative sentiment over time

## Data Flow

1. An Agnost SDK event batch or session payload arrives at `POST /ingest`.
2. The ingest layer validates the payload and stores the raw session immediately.
3. A worker fetches unprocessed sessions in small batches.
4. The worker embeds the conversation text, scores sentiment, and finds nearest neighbors or cluster membership.
5. The worker assigns or updates a topic, writes a topic summary, and records the conversation's sentiment and cluster association.
6. The worker writes a time-bucketed trend snapshot.
7. The API serves topics, trends, alerts, and sample conversations from persisted aggregates.

Idempotency requirement:

- Each session must be safe to process more than once without double-counting topic volume or trend rows.

## API Design

### `GET /topics`

Returns the current topic list, sortable by recency, volume, growth, or negative sentiment.

Example fields:

- `topic_id`
- `label`
- `volume`
- `growth_24h`
- `negative_share`
- `first_seen`
- `last_seen`

### `GET /topics/{topic_id}`

Returns topic detail including:

- summary
- sentiment distribution
- growth curve
- representative conversations
- keywords or nearest-neighbor examples

### `GET /trends`

Returns time-bucketed topic growth and sentiment shifts.

### `GET /alerts`

Returns emerging negative topics ranked by severity and confidence.

Alert payloads should include:

- short explanation
- growth signal
- sentiment signal
- representative snippets

## Error Handling

### Ingestion failures

- Reject invalid payloads with a clear 4xx response
- Persist only validated sessions
- Return enough detail to debug schema issues without exposing internals

### Processing failures

- Mark a session as pending or failed instead of dropping it
- Reprocess failed sessions from the durable raw store
- Keep the raw session record even if embedding or clustering fails

### Clustering instability

- Treat low-confidence sessions as unassigned until enough evidence accumulates
- Allow a later worker pass to reassign topics as clusters stabilize

### Duplicate delivery

- Deduplicate by `session_id`
- Make topic assignment and trend snapshot writes idempotent

## Scalability Notes

The weekend prototype runs on one machine, but the design should scale to 100k to 1M conversations per day by separating ingestion, processing, and query serving.

Scaling path:

- Split ingestion from workers so ingest stays write-fast
- Increase worker concurrency for embedding and clustering
- Move vector storage from in-memory FAISS to a dedicated vector index if needed
- Keep trend queries on pre-aggregated time buckets instead of scanning raw sessions
- Partition tables by time or tenant if throughput grows

Expected bottlenecks:

- Embedding inference latency
- Re-clustering cost as the corpus grows
- Trend aggregation if snapshots are not precomputed

## Testing Plan

### Unit tests

- Payload validation
- Session normalization
- Sentiment mapping
- Cluster assignment helpers
- Trend snapshot generation

### Integration tests

- Ingest a sample session and confirm it appears in the raw store
- Process a batch and confirm topic assignment and alert generation
- Query `/topics`, `/trends`, and `/alerts` against seeded data

### Behavioral tests

- A repeated refund complaint should cluster with semantically similar complaints even when phrased differently
- A burst of negative sessions should raise a visible alert
- A neutral topic should not be mislabeled as a severe issue without growth or negative sentiment evidence

## Implementation Trade-offs

### Chosen trade-offs

- Single Postgres instance instead of multiple services
- FAISS or `pgvector` instead of a separate managed vector database
- HDBSCAN instead of keyword rules or full supervised classification
- Lightweight LLM labeling only after clustering

### Why these trade-offs fit the assignment

- The build stays weekend-sized
- The architecture still looks production-aware
- The PM output remains the priority
- The system can evolve into a more distributed setup later without changing the contract

## What Would Change With More Time

- Add human review for topic merging and renaming
- Add a dashboard for drill-down and triage
- Add tenant-aware filtering and access control
- Add online topic-evolution logic instead of periodic batch re-clustering
- Add stronger evaluation metrics for topic purity and sentiment accuracy
