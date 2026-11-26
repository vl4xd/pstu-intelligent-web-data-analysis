from pathlib import Path

import pandas as pd
from datasets import concatenate_datasets, load_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "movielens"


def main():
    print("Loading MovieLens from Hugging Face...")

    dataset = load_dataset("ashraq/ml-latest-small")

    # Объединяем все доступные части датасета.
    if hasattr(dataset, "keys"):
        parts = [dataset[split] for split in dataset.keys()]
        data = concatenate_datasets(parts)
    else:
        data = dataset

    df = data.to_pandas()

    required_columns = {
        "user_id",
        "movie_id",
        "rating",
        "title",
        "genres",
    }
    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    # Таблица пользовательских оценок.
    ratings = df[["user_id", "movie_id", "rating"]].copy()
    ratings = ratings.rename(
        columns={"user_id": "userId", "movie_id": "movieId"}
    )

    # Таблица фильмов: одна запись на один movieId.
    movie_columns = ["movie_id", "title", "genres"]
    if "imdbId" in df.columns:
        movie_columns.append("imdbId")

    movies = df[movie_columns].drop_duplicates(
        subset=["movie_id"]
    ).copy()

    movies = movies.rename(columns={"movie_id": "movieId"})

    # Проверки целостности.
    assert ratings["rating"].between(0.5, 5.0).all()
    assert not ratings.duplicated(["userId", "movieId"]).any()
    assert not movies["movieId"].duplicated().any()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ratings.to_csv(OUTPUT_DIR / "ratings.csv", index=False)
    movies.to_csv(OUTPUT_DIR / "movies.csv", index=False)

    print("\nDataset successfully prepared.")
    print(f"Ratings: {len(ratings):,}")
    print(f"Users: {ratings['userId'].nunique():,}")
    print(f"Movies in ratings: {ratings['movieId'].nunique():,}")
    print(f"Movie metadata rows: {len(movies):,}")
    print(f"Rating range: {ratings['rating'].min()} - {ratings['rating'].max()}")
    print(f"Saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
