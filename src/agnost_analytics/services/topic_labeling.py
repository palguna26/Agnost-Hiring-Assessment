from __future__ import annotations

from collections import Counter
import re
from typing import Sequence

STOPWORDS = {
    "a",
    "about",
    "and",
    "any",
    "are",
    "at",
    "be",
    "but",
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
    tokens = _tokens_from_texts(texts)
    if not tokens:
        return ["general"]

    common = [token for token, _ in Counter(tokens).most_common(max_keywords)]
    return common or ["general"]


def build_topic_label(texts: Sequence[str]) -> str:
    keywords = build_topic_keywords(texts, max_keywords=2)
    if len(keywords) == 1:
        return keywords[0].replace("_", " ").title()
    return " / ".join(keyword.replace("_", " ").title() for keyword in keywords)


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
