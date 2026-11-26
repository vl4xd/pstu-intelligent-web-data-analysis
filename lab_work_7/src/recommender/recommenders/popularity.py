
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class PopularityRecommender:
    def fit(self, train: pd.DataFrame):
        # Популярность фильма = количество оценок в train.
        self.popular_items = (
            train.groupby("movieId")
            .agg(
                rating_count=("rating", "count"),
                mean_rating=("rating", "mean"),
            )
            .reset_index()
            .sort_values(
                ["rating_count", "mean_rating", "movieId"],
                ascending=[False, False, True],
            )
        )

        self.rated_by_user = (
            train.groupby("userId")["movieId"]
            .apply(set)
            .to_dict()
        )

        return self

    def recommend(self, user_id: int, k: int = 10):
        seen_items = self.rated_by_user.get(user_id, set())

        candidates = self.popular_items[
            ~self.popular_items["movieId"].isin(seen_items)
        ]

        return candidates.head(k)["movieId"].tolist()


def main():
    train_path = PROJECT_ROOT / "data" / "processed" / "train.csv"
    movies_path = PROJECT_ROOT / "data" / "raw" / "movielens" / "movies.csv"
    output_dir = PROJECT_ROOT / "results" / "recommendations"
    output_dir.mkdir(parents=True, exist_ok=True)

    train = pd.read_csv(train_path)
    movies = pd.read_csv(movies_path)

    model = PopularityRecommender().fit(train)

    # Демонстрация рекомендаций для пользователя №1.
    user_id = 414
    recommendations = model.recommend(user_id, k=10)

    result = pd.DataFrame({"movieId": recommendations})
    result = result.merge(movies, on="movieId", how="left")

    print(f"=== POPULARITY RECOMMENDATIONS FOR USER {user_id} ===")
    print(result.to_string(index=False))

    result.to_csv(
        output_dir / f"popularity_user_{user_id}.csv",
        index=False,
    )

    # Сохраняем общий рейтинг популярности.
    model.popular_items.to_csv(
        output_dir / "popularity_ranking.csv",
        index=False,
    )

    print("\nRecommendations saved to:", output_dir)


if __name__ == "__main__":
    main()
