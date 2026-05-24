from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from typing import Sequence

import numpy as np

EMBEDDING_DIMENSION = 16


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
    tokens = [token for token in text.lower().split() if token]
    if not tokens:
        return vector

    for token in tokens:
        digest = sha256(token.encode("utf-8")).digest()
        index = digest[0] % EMBEDDING_DIMENSION
        weight = 1.0 + digest[1] / 255.0
        vector[index] += weight

    norm = float(np.linalg.norm(vector))
    if norm:
        vector /= norm
    return vector


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
