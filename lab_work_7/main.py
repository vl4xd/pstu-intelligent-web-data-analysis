from pathlib import Path
import argparse
import runpy
import sys

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src" / "recommender"
RECOMMENDERS_DIR = SRC_DIR / "recommenders"

# Добавляем пути для совместимости с импортами в существующих модулях.
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(RECOMMENDERS_DIR))


def load_config():
    config_path = PROJECT_ROOT / "config" / "config.yaml"

    with open(config_path, encoding="utf-8") as file:
        return yaml.safe_load(file)


def run_script(relative_path):
    """Запускает существующий скрипт проекта."""
    script_path = SRC_DIR / relative_path

    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    print(f"\n{'=' * 60}")
    print(f"Running: {relative_path}")
    print("=" * 60)

    runpy.run_path(str(script_path), run_name="__main__")


def recommend(model_name, user_id, k):
    """Строит и сохраняет рекомендации выбранной модели."""
    from recommenders.popularity import PopularityRecommender
    from recommenders.content_based import ContentBasedRecommender
    from recommenders.svd import SVDRecommender
    from recommenders.als import ALSRecommender

    train_path = PROJECT_ROOT / "data" / "processed" / "train.csv"
    movies_path = PROJECT_ROOT / "data" / "raw" / "movielens" / "movies.csv"

    if not train_path.exists():
        raise FileNotFoundError(
            "Train data not found. Run `py main.py split` first."
        )

    train = pd.read_csv(train_path)
    movies = pd.read_csv(movies_path)

    models = {
        "popularity": PopularityRecommender,
        "content_based": ContentBasedRecommender,
        "svd": SVDRecommender,
        "als": ALSRecommender,
    }

    selected_models = (
        list(models.keys()) if model_name == "all" else [model_name]
    )

    output_dir = PROJECT_ROOT / "results" / "recommendations"
    output_dir.mkdir(parents=True, exist_ok=True)

    for name in selected_models:
        print(f"\n=== {name.upper()} RECOMMENDATIONS ===")

        model = models[name]()

        if name == "content_based":
            model.fit(train, movies)
        else:
            model.fit(train)

        recommendations = model.recommend(user_id, k=k)

        result = pd.DataFrame({"movieId": recommendations})
        result = result.merge(movies, on="movieId", how="left")

        display_columns = [
            column for column in ["movieId", "title", "genres"]
            if column in result.columns
        ]

        print(f"User ID: {user_id}")
        print(result[display_columns].to_string(index=False))

        output_path = output_dir / f"{name}_user_{user_id}.csv"
        result.to_csv(output_path, index=False)

        print(f"Saved: {output_path}")

        if name == "popularity":
            model.popular_items.to_csv(
                output_dir / "popularity_ranking.csv",
                index=False,
            )


def evaluate(model_name):
    """Запускает оценку одной или всех моделей."""
    scripts = {
        "popularity": "evaluate_popularity.py",
        "content_based": "evaluate_content_based.py",
        "svd": "evaluate_svd.py",
        "als": "evaluate_als.py",
    }

    selected_models = (
        list(scripts.keys()) if model_name == "all" else [model_name]
    )

    for name in selected_models:
        run_script(scripts[name])


def run_all():
    """Выполняет полный экспериментальный пайплайн."""
    print("\nSTARTING FULL RECOMMENDER SYSTEM EXPERIMENT")

    run_script("eda.py")
    run_script("split.py")

    evaluate("all")

    run_script("compare_models.py")
    run_script("evaluate_diversity.py")

    print("\nFULL EXPERIMENT COMPLETED")
    print("Check results/tables/ and results/figures/")


def build_parser():
    parser = argparse.ArgumentParser(
        description="MovieLens recommendation system CLI"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "eda",
        help="Run exploratory data analysis",
    )

    subparsers.add_parser(
        "split",
        help="Create train/test split",
    )

    recommend_parser = subparsers.add_parser(
        "recommend",
        help="Generate recommendations for a user",
    )
    recommend_parser.add_argument(
        "--model",
        choices=[
            "popularity",
            "content_based",
            "svd",
            "als",
            "all",
        ],
        default="als",
        help="Recommendation model",
    )
    recommend_parser.add_argument(
        "--user-id",
        type=int,
        default=414,
        help="Target user ID (default: 414)",
    )
    recommend_parser.add_argument(
        "-k",
        type=int,
        default=None,
        help="Number of recommendations (default: config value)",
    )

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate recommendation quality",
    )
    evaluate_parser.add_argument(
        "--model",
        choices=[
            "popularity",
            "content_based",
            "svd",
            "als",
            "all",
        ],
        default="all",
        help="Model to evaluate",
    )

    subparsers.add_parser(
        "compare",
        help="Compare evaluation metrics of all models",
    )

    subparsers.add_parser(
        "diversity",
        help="Evaluate recommendation diversity",
    )

    subparsers.add_parser(
        "all",
        help="Run the complete experiment pipeline",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "eda":
        run_script("eda.py")

    elif args.command == "split":
        run_script("split.py")

    elif args.command == "recommend":
        config = load_config()
        k = args.k or config["experiment"]["top_k"]

        if k <= 0:
            parser.error("k must be a positive integer")

        recommend(args.model, args.user_id, k)

    elif args.command == "evaluate":
        evaluate(args.model)

    elif args.command == "compare":
        run_script("compare_models.py")

    elif args.command == "diversity":
        run_script("evaluate_diversity.py")

    elif args.command == "all":
        run_all()


if __name__ == "__main__":
    main()