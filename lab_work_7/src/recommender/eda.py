
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "raw" / "movielens"
RESULTS_DIR = PROJECT_ROOT / "results"


def run_eda():
    ratings = pd.read_csv(DATA_DIR / "ratings.csv")
    movies = pd.read_csv(DATA_DIR / "movies.csv")

    # Основные размеры датасета
    n_users = ratings["userId"].nunique()
    n_items = ratings["movieId"].nunique()
    n_ratings = len(ratings)

    # Плотность и разреженность матрицы
    total_cells = n_users * n_items
    density = n_ratings / total_cells
    sparsity = 1 - density

    # Активность пользователей
    user_activity = ratings.groupby("userId").size()

    # Активность фильмов
    item_activity = ratings.groupby("movieId").size()

    print("=== DATASET OVERVIEW ===")
    print(f"Ratings: {n_ratings:,}")
    print(f"Users: {n_users:,}")
    print(f"Movies: {n_items:,}")
    print(f"Movie metadata rows: {len(movies):,}")

    print("\n=== MATRIX SPARSITY ===")
    print(f"Matrix size: {n_users} x {n_items}")
    print(f"Density: {density:.4%}")
    print(f"Sparsity: {sparsity:.4%}")

    print("\n=== USER ACTIVITY ===")
    print(user_activity.describe())

    print("\n=== ITEM ACTIVITY ===")
    print(item_activity.describe())

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "figures").mkdir(exist_ok=True)
    (RESULTS_DIR / "tables").mkdir(exist_ok=True)

    # Сохраняем числовую сводку
    summary = pd.DataFrame({
        "metric": [
            "ratings",
            "users",
            "movies",
            "density",
            "sparsity",
            "mean_ratings_per_user",
            "median_ratings_per_user",
            "mean_ratings_per_movie",
        ],
        "value": [
            n_ratings,
            n_users,
            n_items,
            density,
            sparsity,
            user_activity.mean(),
            user_activity.median(),
            item_activity.mean(),
        ],
    })

    summary.to_csv(
        RESULTS_DIR / "tables" / "eda_summary.csv",
        index=False,
    )

    # Распределение активности пользователей
    plt.figure(figsize=(8, 5))
    plt.hist(user_activity, bins=30, edgecolor="black")
    plt.title("Ratings per user")
    plt.xlabel("Number of ratings")
    plt.ylabel("Number of users")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "figures" / "user_activity.png")
    plt.close()

    # Распределение оценок
    plt.figure(figsize=(8, 5))
    ratings["rating"].value_counts().sort_index().plot(kind="bar")
    plt.title("Rating distribution")
    plt.xlabel("Rating")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "figures" / "rating_distribution.png")
    plt.close()

    print("\nEDA results saved to results/")


if __name__ == "__main__":
    run_eda()
