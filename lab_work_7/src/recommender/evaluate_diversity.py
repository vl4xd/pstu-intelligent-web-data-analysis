
from pathlib import Path
from itertools import combinations

import pandas as pd

from recommenders.popularity import PopularityRecommender
from recommenders.content_based import ContentBasedRecommender
from recommenders.svd import SVDRecommender
from recommenders.als import ALSRecommender


PROJECT_ROOT = Path(__file__).resolve().parents[2]
K = 10


def get_genres(genres_string):
    if pd.isna(genres_string) or genres_string == "(no genres listed)":
        return set()

    return set(genres_string.split("|"))


def intra_list_diversity(recommendations, movie_genres):
    if len(recommendations) < 2:
        return 0.0

    distances = []

    for item_a, item_b in combinations(recommendations, 2):
        genres_a = movie_genres.get(item_a, set())
        genres_b = movie_genres.get(item_b, set())

        union = genres_a | genres_b

        if not union:
            similarity = 0.0
        else:
            similarity = len(genres_a & genres_b) / len(union)

        distances.append(1.0 - similarity)

    return sum(distances) / len(distances)


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

    movie_genres = {
        row.movieId: get_genres(row.genres)
        for row in movies.itertuples()
    }

    users = sorted(
        test[test["rating"] >= 4.0]["userId"].unique()
    )

    models = {
        "Popularity": PopularityRecommender().fit(train),
        "Content-based TF-IDF": ContentBasedRecommender().fit(
            train, movies
        ),
        "Collaborative SVD": SVDRecommender().fit(train),
        "Implicit ALS": ALSRecommender().fit(train),
    }

    results = []

    for model_name, model in models.items():
        user_ild = []
        all_recommended = set()
        all_genres = set()

        for user_id in users:
            recommendations = model.recommend(user_id, k=K)

            all_recommended.update(recommendations)

            user_ild.append(
                intra_list_diversity(
                    recommendations, movie_genres
                )
            )

            for movie_id in recommendations:
                all_genres.update(
                    movie_genres.get(movie_id, set())
                )

        results.append({
            "model": model_name,
            "evaluated_users": len(users),
            "mean_ILD": sum(user_ild) / len(user_ild),
            "unique_recommended_movies": len(all_recommended),
            "unique_genres": len(all_genres),
            "catalog_coverage": len(all_recommended) / len(movies),
        })

    comparison = pd.DataFrame(results)

    output_dir = PROJECT_ROOT / "results" / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)

    comparison.to_csv(
        output_dir / "diversity_comparison.csv",
        index=False
    )

    print("=== DIVERSITY COMPARISON ===")
    print(comparison.to_string(index=False))
    print("\nSaved:", output_dir / "diversity_comparison.csv")


if __name__ == "__main__":
    main()
