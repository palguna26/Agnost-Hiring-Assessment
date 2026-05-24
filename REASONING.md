# Reasoning

## Database choice
PostgreSQL is the right default for this prototype because it keeps the system to one operational dependency while covering the three data shapes the app needs: raw conversations, topic rows, and time-bucketed trend snapshots. It is easy to inspect locally, works cleanly with SQLAlchemy and Alembic, and matches the implemented models without introducing a second storage engine.

The trade-off is that PostgreSQL is not the fastest path for very large vector workloads or high-frequency analytics, but that is acceptable here. The assignment values a working, debuggable system more than a production-scale infrastructure stack.

## Clustering choice
Sentence embeddings plus HDBSCAN is a good fit for evolving support topics because it groups semantically similar user requests without forcing a fixed number of clusters. HDBSCAN also handles noise better than keyword rules, which matters when support traffic includes mixed intents, one-off complaints, and short messages.

The worker keeps deterministic fallbacks so the project still runs in a minimal environment, but the intended path is embedding-based clustering with periodic refreshes. The trade-off is that topic quality depends on user text quality and embedding availability, so cluster labels are approximate rather than human-curated.

To avoid over-promoting tiny, obviously unrelated groups, the clustering layer also demotes small two-point clusters when the vectors are too far apart. That keeps the weekend prototype conservative rather than inventing topic structure from noise.

## SDK choice
The ingest API accepts Agnost SDK-shaped payloads because that keeps the contract realistic while still making local development easy. The accepted payloads are JSON objects with session metadata, message arrays, and optional metadata, which means the same shape can be replayed from a webhook, a file, or a future SDK client.

The trade-off is that the prototype does not depend on a real upstream SDK at runtime, so the integration boundary is modeled rather than hard-coupled. That is the right split for an assessment: preserve the product shape without introducing unnecessary external dependencies.

## Trade-offs
This build intentionally favors one PostgreSQL instance, a simple FastAPI surface, and a background worker over extra infrastructure. That keeps setup friction low and makes debugging straightforward, but it means the prototype is batch-oriented and not tuned for large-scale online clustering.

That is the correct trade for the assignment. It proves the product loop first, keeps the API usable, and leaves room to swap in stronger storage or clustering services later.

## With A Month
With another month, I would add a human review loop for topic merging and naming, stronger evaluation for topic quality and sentiment accuracy, and a real vector store or managed embedding index instead of the current lightweight fallback path. I would also add tenant-aware filtering, a simple dashboard for PM exploration, and more explicit alert tuning so the system can separate new product issues from general support noise more reliably.
