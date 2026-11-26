
from pathlib import Path
import pandas as pd

from content_based import ContentBasedRecommender


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def main():
    train = pd.read_csv(
        PROJECT_ROOT / "data" / "processed" / "train.csv"
    )
    movies = pd.read_csv(
        PROJECT_ROOT / "data" / "raw" / "movielens" / "movies.csv"
    )

    model = ContentBasedRecommender().fit(train, movies)

    user_id = 414
    recommendations = model.recommend(user_id, k=10)

    result = pd.DataFrame({"movieId": recommendations})
    result = result.merge(movies, on="movieId", how="left")

    print(f"=== CONTENT-BASED RECOMMENDATIONS FOR USER {user_id} ===")
    print(result[["movieId", "title", "genres"]].to_string(index=False))

    output_dir = PROJECT_ROOT / "results" / "recommendations"
    output_dir.mkdir(parents=True, exist_ok=True)

    result.to_csv(
        output_dir / f"content_based_user_{user_id}.csv",
        index=False
    )

    print("\nRecommendations saved to:", output_dir)


if __name__ == "__main__":
    main()
