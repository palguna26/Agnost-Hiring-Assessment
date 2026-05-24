from __future__ import annotations

from collections import Counter
import re
from typing import Sequence

from agnost_analytics.services.embeddings import SEMANTIC_BUCKET_ORDER, semantic_signature

DISPLAY_NAME_MAP = {
    "billing_refund": "Refund",
    "feature_dark_mode": "Dark Mode",
    "feature_request": "Feature Request",
    "support_issue": "Issue",
    "positive_resolution": "Resolved",
}

STOPWORDS = {
    "a",
    "about",
    "and",
    "any",
    "are",
    "at",
    "be",
    "but",
    "can",
    "for",
    "from",
    "have",
    "help",
    "i",
    "in",
    "is",
    "it",
    "my",
    "need",
    "not",
    "on",
    "please",
    "problem",
    "support",
    "the",
    "this",
    "to",
    "was",
    "we",
    "with",
    "you",
}

WORD_RE = re.compile(r"[a-z0-9']+")


def _tokens_from_texts(texts: Sequence[str]) -> list[str]:
    tokens: list[str] = []
    for text in texts:
        for token in WORD_RE.findall(text.lower()):
            if token in STOPWORDS or len(token) <= 2:
                continue
            tokens.append(token)
    return tokens


def build_topic_keywords(texts: Sequence[str], max_keywords: int = 3) -> list[str]:
    signatures = [signature for text in texts if (signature := semantic_signature(text)) and signature != ("general",)]
    semantic_keywords: list[str] = []
    for signature in signatures:
        for token in signature:
            if token in SEMANTIC_BUCKET_ORDER and token not in semantic_keywords:
                semantic_keywords.append(token)

    if semantic_keywords:
        return semantic_keywords[:max_keywords]

    tokens = _tokens_from_texts(texts)
    if not tokens:
        return ["general"]

    common = [token for token, _ in Counter(tokens).most_common(max_keywords)]
    return common or ["general"]


def build_topic_label(texts: Sequence[str]) -> str:
    keywords = build_topic_keywords(texts, max_keywords=2)
    if len(keywords) == 1:
        return DISPLAY_NAME_MAP.get(keywords[0], keywords[0].replace("_", " ").title())
    return " / ".join(
        DISPLAY_NAME_MAP.get(keyword, keyword.replace("_", " ").title()) for keyword in keywords
    )


def build_topic_summary(texts: Sequence[str], keywords: Sequence[str] | None = None) -> str:
    keywords = list(keywords) if keywords is not None else build_topic_keywords(texts)
    sample = next((text.strip() for text in texts if text.strip()), "")
    summary = f"Common themes: {', '.join(keywords)}."
    if sample:
        summary += f" Example: {sample[:160]}"
    return summary


def label_topic(texts: Sequence[str]) -> tuple[str, str, list[str]]:
    keywords = build_topic_keywords(texts)
    return build_topic_label(texts), build_topic_summary(texts, keywords), keywords
