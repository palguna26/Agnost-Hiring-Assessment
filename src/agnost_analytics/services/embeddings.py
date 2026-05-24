from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
import re
from typing import Sequence

import numpy as np

EMBEDDING_DIMENSION = 64

WORD_RE = re.compile(r"[a-z0-9']+")

DOMAIN_TOKEN_MAP: dict[str, str] = {
    "add": "feature_request",
    "feature": "feature_request",
    "dark": "feature_dark_mode",
    "mode": "feature_dark_mode",
    "theme": "feature_dark_mode",
    "ui": "feature_request",
    "refund": "billing_refund",
    "refunded": "billing_refund",
    "charge": "billing_refund",
    "charged": "billing_refund",
    "chargedtwice": "billing_refund",
    "duplicate": "billing_refund",
    "billing": "billing_refund",
    "card": "billing_refund",
    "invoice": "billing_refund",
    "cancel": "billing_refund",
    "issue": "support_issue",
    "bug": "support_issue",
    "broken": "support_issue",
    "error": "support_issue",
    "fixed": "positive_resolution",
    "resolved": "positive_resolution",
    "thanks": "positive_resolution",
    "thank": "positive_resolution",
    "works": "positive_resolution",
    "working": "positive_resolution",
    "helpful": "positive_resolution",
    "happy": "positive_resolution",
}

SUPPORT_BIGRAMS: dict[tuple[str, str], str] = {
    ("dark", "mode"): "feature_dark_mode",
    ("duplicate", "charge"): "billing_refund",
    ("charged", "twice"): "billing_refund",
    ("need", "refund"): "billing_refund",
    ("want", "refund"): "billing_refund",
    ("issue", "fixed"): "positive_resolution",
    ("is", "fixed"): "positive_resolution",
    ("thank", "you"): "positive_resolution",
}

SEMANTIC_BUCKET_ORDER = (
    "billing_refund",
    "feature_dark_mode",
    "feature_request",
    "support_issue",
    "positive_resolution",
)


@lru_cache(maxsize=1)
def _sentence_transformer_model():
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None

    try:
        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


def _fallback_embedding(text: str) -> np.ndarray:
    vector = np.zeros(EMBEDDING_DIMENSION, dtype=float)
    tokens = [token for token in WORD_RE.findall(text.lower()) if token]
    if not tokens:
        return vector

    canonical_tokens = [_canonicalize_token(token) for token in tokens]
    canonical_tokens = [token for token in canonical_tokens if token]

    features: list[str] = list(canonical_tokens)
    features.extend(
        feature
        for feature in _canonical_bigrams(tokens)
        if feature
    )

    for token in features:
        digest = sha256(token.encode("utf-8")).digest()
        index = digest[0] % EMBEDDING_DIMENSION
        weight = 1.0 + digest[1] / 255.0
        vector[index] += weight

    norm = float(np.linalg.norm(vector))
    if norm:
        vector /= norm
    return vector


def semantic_signature(text: str) -> tuple[str, ...]:
    tokens = [token for token in WORD_RE.findall(text.lower()) if token]
    if not tokens:
        return ("general",)

    canonical_tokens = [_canonicalize_token(token) for token in tokens]
    canonical_tokens = [token for token in canonical_tokens if token]
    canonical_tokens.extend(_canonical_bigrams(tokens))

    bucketed = [token for token in canonical_tokens if token in SEMANTIC_BUCKET_ORDER]
    if bucketed:
        ordered = [token for token in SEMANTIC_BUCKET_ORDER if token in bucketed]
        if "positive_resolution" in ordered and "support_issue" in ordered:
            return ("positive_resolution",)
        return tuple(ordered)

    unique = []
    for token in canonical_tokens:
        if token not in unique:
            unique.append(token)

    return tuple(unique[:4]) or ("general",)


def _canonicalize_token(token: str) -> str:
    normalized = token.strip("'")
    if normalized in DOMAIN_TOKEN_MAP:
        return DOMAIN_TOKEN_MAP[normalized]

    if normalized.endswith("ed") and normalized[:-2] in DOMAIN_TOKEN_MAP:
        return DOMAIN_TOKEN_MAP[normalized[:-2]]
    if normalized.endswith("s") and normalized[:-1] in DOMAIN_TOKEN_MAP:
        return DOMAIN_TOKEN_MAP[normalized[:-1]]

    return normalized


def _canonical_bigrams(tokens: Sequence[str]) -> list[str]:
    bigrams: list[str] = []
    for first, second in zip(tokens, tokens[1:]):
        pair = (first, second)
        if pair in SUPPORT_BIGRAMS:
            bigrams.append(SUPPORT_BIGRAMS[pair])
            continue

        canonical_pair = (_canonicalize_token(first), _canonicalize_token(second))
        if canonical_pair in SUPPORT_BIGRAMS:
            bigrams.append(SUPPORT_BIGRAMS[canonical_pair])
            continue

        if canonical_pair[0] and canonical_pair[1]:
            bigrams.append(f"{canonical_pair[0]}__{canonical_pair[1]}")

    return bigrams


def embed_conversations(texts: Sequence[str]) -> np.ndarray:
    """Embed conversation texts into dense vectors.

    The production path uses sentence-transformers when available. Tests and
    lightweight local runs fall back to a deterministic hashed embedding so the
    worker still behaves predictably without extra model downloads.
    """

    model = _sentence_transformer_model()
    cleaned_texts = [text[:512] for text in texts]

    if model is not None:
        embeddings = model.encode(cleaned_texts, normalize_embeddings=True)
        return np.asarray(embeddings, dtype=float)

    return np.asarray([_fallback_embedding(text) for text in cleaned_texts], dtype=float)
