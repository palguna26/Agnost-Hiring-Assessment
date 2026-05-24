Assignment: Sentiment Analytics Engine for Conversational AI Agents
Background
Agnost is an analytics platform built specifically for conversational AI agents. Unlike traditional web analytics (page views, bounce rates), conversational agents generate unstructured text data—user messages, agent responses, tool calls, and session trails. Product managers (PMs) at companies using Agnost need to answer questions like:

“Why are 20% of users requesting refunds this week?”

“What hidden feature requests are emerging from power users?”

“How do users feel about the new pricing model?”

Manually reading thousands of conversations is impossible. Your task is to build an automated sentiment analytics engine that ingests raw conversation logs, clusters emerging topics, quantifies sentiment, and surfaces actionable PM insights.

Your Track: AI Engineer First
You will design and implement a working prototype (in a GitHub repo) that demonstrates the core pipeline. You will also document your reasoning thoroughly.

Problem Statement (Core Requirements)
Build a system that:

Ingests a stream of user–agent conversations (you may assume any reasonable API schema – define it in your docs).

Automatically clusters conversations into emerging topics (e.g., “refund requests due to duplicate charge”, “feature request: dark mode”).

Assigns sentiment per conversation (positive/negative/neutral) and aggregates sentiment per topic.

Generates PM‑friendly insights – e.g., “Topic X has grown 200% in last 3 days with 85% negative sentiment – likely a bug.”

Exposes a simple, usable API that a PM or dashboard could query to get current topics, trends, and sample conversations.

Deliverables
You must submit:

A REASONING.md file (in your repo) that explains:

Your choice of database(s) (time‑series, vector, relational – justify each)

Your choice of clustering algorithm(s) (and why you rejected alternatives)

Your choice of SDK / ingestion method (why Agnost SDK vs raw webhooks)

Any major trade‑offs you made

Architecture documentation (1‑2 pages in the repo, diagrams + bullets) that shows:

Data flow from agent to insight

Components (ingestion, processing, storage, API)

Scalability notes (how it would handle 1M+ conversations/day)

A working GitHub repository with:

Runnable code (Python preferred – FastAPI/Flask, plus any clustering/sentiment libraries)

A README.md that explains how to run it locally (docker‑compose or pip + script)

At least two usable API endpoints (e.g., GET /topics, GET /trends)

A mock agent script or sample data to demonstrate the pipeline

Constraints & Assumptions
Time: Build as if you have a weekend (but document what you’d change with a month).

Data: You may assume any dataset schema you like – but you must document it in your REASONING.md (e.g., fields: session_id, timestamp, messages array, user_id).

Scalability: Your design should be able to handle 100k–1M conversations per day. The weekend prototype may run on a single machine, but your reasoning must explain how it scales.

External APIs: You may use any pre‑trained models (Hugging Face, OpenAI, etc.) but must justify cost/latency trade‑offs.

Agnost integration: Assume the conversational agent already uses the Agnost SDK to emit logs. You will receive those logs via a webhook or a stream. Mock this integration if needed – but explain how it would work with real Agnost.

Evaluation Criteria (The “Bar”)
Reasoning: Every major choice (DB, clustering, SDK, API design) is explained with pros/cons and rejected alternatives.

Taste: The system is appropriately simple for a weekend, but the architecture shows awareness of production realities (scalability, latency, maintainability).

Judgment: You prioritise what matters for PM insights (trend detection, sentiment, topic quality) over vanity features.

Optional (Stretch Goals)
Real‑time or near‑real‑time topic emergence detection.

Automatic labelling of clusters using a small LLM (e.g., GPT‑3.5‑turbo).

Integration with a dashboard (Streamlit or Agnost UI mock).

Tests for the clustering pipeline.