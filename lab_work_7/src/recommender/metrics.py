
import math


def precision_at_k(recommended: list, relevant: set, k: int = 10) -> float:
    """Доля релевантных фильмов среди первых k рекомендаций."""
    if k <= 0:
        return 0.0

    top_k = recommended[:k]
    if not top_k:
        return 0.0

    hits = sum(item in relevant for item in top_k)
    return hits / k


def recall_at_k(recommended: list, relevant: set, k: int = 10) -> float:
    """Доля найденных релевантных фильмов."""
    if not relevant or k <= 0:
        return 0.0

    hits = sum(item in relevant for item in recommended[:k])
    return hits / len(relevant)


def average_precision_at_k(
    recommended: list, relevant: set, k: int = 10
) -> float:
    """Средняя точность с учётом позиции релевантных рекомендаций."""
    if not relevant or k <= 0:
        return 0.0

    hits = 0
    score = 0.0

    for rank, item in enumerate(recommended[:k], start=1):
        if item in relevant:
            hits += 1
            score += hits / rank

    denominator = min(len(relevant), k)
    return score / denominator


def ndcg_at_k(recommended: list, relevant: set, k: int = 10) -> float:
    """Нормализованный дисконтированный накопленный выигрыш."""
    if not relevant or k <= 0:
        return 0.0

    dcg = sum(
        1 / math.log2(rank + 1)
        for rank, item in enumerate(recommended[:k], start=1)
        if item in relevant
    )

    ideal_hits = min(len(relevant), k)
    idcg = sum(
        1 / math.log2(rank + 1)
        for rank in range(1, ideal_hits + 1)
    )

    return dcg / idcg if idcg else 0.0
