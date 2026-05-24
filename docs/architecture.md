# Architecture

## Overview
The app is a small FastAPI service backed by PostgreSQL. Conversations arrive through `/ingest`, are stored as raw rows, and are then enriched by the worker into topics and time-bucketed trend snapshots. The query endpoints read only the persisted aggregates.

## Components
- FastAPI app: exposes `/health`, `/ingest`, `/topics`, `/topics/{topic_id}`, `/trends`, and `/alerts`.
- PostgreSQL: stores `conversations`, `topics`, and `topic_trend_snapshots`.
- Worker: reads pending conversations, computes embeddings and sentiment, assigns topics, and updates trend aggregates.
- Sample data: JSONL fixture plus a small generator script for replayable local data.

## Data Flow
1. A client posts an Agnost SDK-shaped payload to `/ingest`.
2. The API validates the payload and persists the raw conversation with `analysis_status="pending"`.
3. The worker reads pending rows, calculates embeddings and sentiment from user-authored turns, clusters related conversations, and updates topic summaries.
4. The worker writes bucketed trend snapshots for each topic.
5. The query API serves PM-facing views from the stored topic and trend tables.

## Query Surfaces
- `/topics` returns a ranked list of topics in an `{"items": [...]}` envelope.
- `/topics/{topic_id}` returns one topic with sentiment distribution, keywords, representative conversations, and growth data.
- `/trends` returns bucketed trend rows in an `{"items": [...]}` envelope.
- `/alerts` returns topics that cross the growth, negativity, and severity thresholds.

## Local Shape
The prototype stays intentionally simple: one database, one API process, and one worker loop. That is enough to demonstrate the product loop without introducing separate services for vectors, queues, or analytics storage.
