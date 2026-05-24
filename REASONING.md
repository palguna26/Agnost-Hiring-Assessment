# Reasoning

I treated this as a weekend prototype, so I started with one question: what is the smallest system that still feels real to a PM reading the output?

The answer I landed on was a single FastAPI service with PostgreSQL behind it, a background worker doing the analysis, and a small set of API endpoints that expose the result in plain language. That kept the system simple enough to build and debug, but still close to the shape of a product someone could actually use.

## How I chose the database

I kept coming back to PostgreSQL because it covers the three kinds of data this app needs without making the deployment feel like a science project.

Raw conversations fit naturally in relational tables. Topic summaries and topic stats also fit there. And the time-bucketed trend snapshots are easy to store and query in the same place. That means one database, one migration path, one mental model.

I did not add a separate vector database or analytics store because that would have made the demo harder to reason about and harder to run locally. PostgreSQL is not the absolute best tool for every workload here, but it is the right one for this assignment because it keeps the prototype understandable and debuggable.

If this were a larger production system, I would probably split vectors and analytics into separate services later. For the weekend version, that would be extra architecture without enough payoff.

## How I chose the clustering approach

The goal was not to sort conversations by keywords. The goal was to notice when people were talking about the same thing even if they used different words.

That is why I used sentence embeddings plus HDBSCAN. Embeddings let the model compare meaning rather than exact phrasing, and HDBSCAN is useful because it does not force every conversation into a cluster. That matters a lot in support traffic, where some messages are real themes, some are noise, and some are one-off edge cases.

I also kept deterministic fallbacks in place so the project still runs in a lightweight environment. The fallback path is intentionally conservative. If a tiny cluster looks too unstable or too far apart, it gets treated as noise instead of being turned into a fake topic. I would rather miss a weak topic than invent a bad one.

There is still a trade-off: the quality of the topics depends on the quality of the user text and the embeddings available at runtime. That is acceptable for this prototype because the assignment values a working PM insight loop more than a perfect topic model.

## Why the SDK-shaped ingest exists

I made the ingest API accept Agnost SDK-shaped payloads because that keeps the contract realistic without tying the prototype to a specific upstream runtime.

The payload shape is simple: session metadata, a message array, and optional metadata. That is enough to mock a webhook, replay a file, or later connect a real SDK client. It also keeps the ingest boundary honest. The system behaves like it is receiving production logs, but it does not need a live external dependency just to run locally.

That seemed like the right compromise for an assessment. It preserves the product story without making the implementation brittle.

## What I chose not to build

I kept the build intentionally small: one database, one API, one worker. No queue service. No dedicated vector store. No dashboard. No user-facing moderation loop.

That is not because those things are unimportant. It is because they would have made the prototype slower to understand and harder to verify, while not improving the actual PM value very much. The important thing here is the loop from conversation to topic to insight. Everything else can wait.

The upside of that choice is speed and clarity. The downside is that the system is batch-oriented and not tuned for huge online workloads. That is fine for now because the assignment asked for a working repo that is simpler and easier, not an overbuilt platform.

## What I would do with a month

With more time, I would harden the system in the places that matter most:

- add a human review loop for merging and renaming topics
- evaluate topic quality more rigorously instead of relying on intuition
- improve alert tuning so it separates real product issues from general support noise
- add tenant-aware filtering and a small PM dashboard
- replace the lightweight vector fallback with a real vector store or managed embedding index

The weekend version proves the loop. The month-long version would make that loop trustworthy enough for a real team to depend on.
