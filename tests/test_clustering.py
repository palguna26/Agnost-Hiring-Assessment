from __future__ import annotations

import numpy as np

from agnost_analytics.services.clustering import cluster_embeddings


def test_similar_refund_complaints_cluster_together() -> None:
    embeddings = np.array(
        [
            [0.00, 0.00],
            [0.02, 0.01],
            [10.0, 10.0],
        ],
        dtype=float,
    )

    labels = cluster_embeddings(embeddings, min_cluster_size=2)
    assert labels[0] == labels[1]
    assert labels[2] == -1


def test_single_embedding_is_treated_as_noise() -> None:
    embeddings = np.array([[1.0, 2.0]], dtype=float)

    labels = cluster_embeddings(embeddings, min_cluster_size=2)
    assert labels == [-1]


def test_distant_pair_is_treated_as_noise() -> None:
    embeddings = np.array(
        [
            [0.0, 0.0],
            [10.0, 10.0],
        ],
        dtype=float,
    )

    labels = cluster_embeddings(embeddings, min_cluster_size=2)
    assert labels == [-1, -1]
