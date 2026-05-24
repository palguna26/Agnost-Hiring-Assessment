from __future__ import annotations

from collections import deque

import numpy as np


def _fallback_cluster_embeddings(embeddings: np.ndarray, min_cluster_size: int) -> list[int]:
    if embeddings.size == 0:
        return []

    matrix = np.asarray(embeddings, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("embeddings must be a 2D array")
    if len(matrix) == 1:
        return [-1]

    distances = np.linalg.norm(matrix[:, None, :] - matrix[None, :, :], axis=2)
    nearest_neighbor_distances: list[float] = []
    for index in range(len(matrix)):
        row = np.delete(distances[index], index)
        nearest_neighbor_distances.append(float(row.min()))

    eps = max(float(np.median(nearest_neighbor_distances)) * 2.5, 1e-6)
    adjacency = {
        index: {neighbor for neighbor in range(len(matrix)) if index != neighbor and distances[index, neighbor] <= eps}
        for index in range(len(matrix))
    }

    labels = [-1] * len(matrix)
    visited = set()
    cluster_id = 0

    for index in range(len(matrix)):
        if index in visited:
            continue

        visited.add(index)
        neighbors = adjacency[index] | {index}
        if len(neighbors) < min_cluster_size:
            continue

        queue = deque(neighbors)
        cluster_members: set[int] = set()
        while queue:
            candidate = queue.popleft()
            if candidate in cluster_members:
                continue
            cluster_members.add(candidate)
            visited.add(candidate)
            candidate_neighbors = adjacency[candidate] | {candidate}
            if len(candidate_neighbors) >= min_cluster_size:
                for neighbor in candidate_neighbors:
                    if neighbor not in cluster_members:
                        queue.append(neighbor)

        for member in cluster_members:
            labels[member] = cluster_id
        cluster_id += 1

    return labels


def cluster_embeddings(embeddings: np.ndarray, min_cluster_size: int = 2) -> list[int]:
    """Cluster embeddings with HDBSCAN when available, otherwise fall back."""

    matrix = np.asarray(embeddings, dtype=float)
    if matrix.size == 0:
        return []

    try:
        import hdbscan
    except Exception:
        labels = _fallback_cluster_embeddings(matrix, min_cluster_size)
        return _stabilize_small_clusters(matrix, labels)

    try:
        clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size)
        labels = list(clusterer.fit_predict(matrix))
    except Exception:
        labels = _fallback_cluster_embeddings(matrix, min_cluster_size)

    labels = _stabilize_small_clusters(matrix, labels)
    return labels


def _stabilize_small_clusters(matrix: np.ndarray, labels: list[int]) -> list[int]:
    if len(matrix) != len(labels) or len(matrix) < 2:
        return labels

    cluster_members: dict[int, list[int]] = {}
    for index, label in enumerate(labels):
        if label == -1:
            continue
        cluster_members.setdefault(label, []).append(index)

    for members in cluster_members.values():
        if len(members) != 2:
            continue

        first, second = members
        distance = float(np.linalg.norm(matrix[first] - matrix[second]))
        if distance > 0.35:
            labels[first] = -1
            labels[second] = -1

    return labels
