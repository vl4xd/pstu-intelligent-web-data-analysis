
from pathlib import Path
import pandas as pd

from metrics import (
    precision_at_k,
    recall_at_k,
    average_precision_at_k,
    ndcg_at_k,
)
from recommenders.content_based import ContentBasedRecommender

PROJECT_ROOT = Path(__file__).resolve().parents[2]
K = 10
POSITIVE_THRESHOLD = 4.0


def main():
    train = pd.read_csv(
        PROJECT_ROOT / "data" / "processed" / "train.csv"
    )
    test = pd.read_csv(
        PROJECT_ROOT / "data" / "processed" / "test.csv"
    )
    movies = pd.read_csv(
        PROJECT_ROOT / "data" / "raw" / "movielens" / "movies.csv"
    )

    relevant_by_user = (
        test[test["rating"] >= POSITIVE_THRESHOLD]
        .groupby("userId")["movieId"]
        .apply(set)
        .to_dict()
    )

    model = ContentBasedRecommender().fit(train, movies)

    user_results = []
    all_recommended = set()
    users_without_recommendations = 0

    for user_id, relevant_items in relevant_by_user.items():
        recommendations = model.recommend(user_id, k=K)

        if not recommendations:
            users_without_recommendations += 1

        all_recommended.update(recommendations)

        user_results.append({
            "userId": user_id,
            "precision@10": precision_at_k(
                recommendations, relevant_items, K
            ),
            "recall@10": recall_at_k(
                recommendations, relevant_items, K
            ),
            "map@10": average_precision_at_k(
                recommendations, relevant_items, K
            ),
            "ndcg@10": ndcg_at_k(
                recommendations, relevant_items, K
            ),
        })

    user_metrics = pd.DataFrame(user_results)

    summary = pd.DataFrame([{
        "model": "Content-based TF-IDF",
        "k": K,
        "evaluated_users": len(user_metrics),
        "users_without_recommendations": users_without_recommendations,
        "precision@10": user_metrics["precision@10"].mean(),
        "recall@10": user_metrics["recall@10"].mean(),
        "map@10": user_metrics["map@10"].mean(),
        "ndcg@10": user_metrics["ndcg@10"].mean(),
        "catalog_coverage": len(all_recommended) / len(movies),
    }])

    output_dir = PROJECT_ROOT / "results" / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)

    user_metrics.to_csv(
        output_dir / "content_based_user_metrics.csv",
        index=False
    )
    summary.to_csv(
        output_dir / "content_based_metrics.csv",
        index=False
    )

    print("=== CONTENT-BASED EVALUATION ===")
    print(summary.to_string(index=False))
    print("\nEvaluated users:", len(user_metrics))
    print("Users without recommendations:", users_without_recommendations)
    print("Results saved to:", output_dir)


if __name__ == "__main__":
    main()
