
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config():
    with open(PROJECT_ROOT / "config" / "config.yaml", encoding="utf-8") as file:
        return yaml.safe_load(file)


def create_split():
    config = load_config()
    experiment = config["experiment"]

    data_dir = PROJECT_ROOT / config["dataset"]["data_dir"]
    ratings = pd.read_csv(data_dir / "ratings.csv")

    test_size = experiment["test_size"]
    random_state = experiment["random_state"]

    # Выбираем 20% оценок каждого пользователя в test.
    test = (
        ratings.groupby("userId", group_keys=False)
        .sample(frac=test_size, random_state=random_state)
    )

    # Все остальные оценки отправляем в train.
    train = ratings.drop(index=test.index).copy()

    # Проверяем отсутствие пересечений.
    train_pairs = set(zip(train["userId"], train["movieId"]))
    test_pairs = set(zip(test["userId"], test["movieId"]))

    assert train_pairs.isdisjoint(test_pairs)

    # Проверяем, что каждый пользователь присутствует в обеих частях.
    assert set(train["userId"]) == set(test["userId"])

    output_dir = PROJECT_ROOT / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    train.to_csv(output_dir / "train.csv", index=False)
    test.to_csv(output_dir / "test.csv", index=False)

    threshold = experiment["positive_threshold"]
    relevant_test = test[test["rating"] >= threshold]

    print("=== EXPERIMENT SPLIT ===")
    print(f"Train ratings: {len(train):,}")
    print(f"Test ratings: {len(test):,}")
    print(f"Train users: {train['userId'].nunique():,}")
    print(f"Test users: {test['userId'].nunique():,}")
    print(f"Positive test interactions (rating >= {threshold}): {len(relevant_test):,}")
    print(f"Train ratio: {len(train) / len(ratings):.2%}")
    print(f"Test ratio: {len(test) / len(ratings):.2%}")
    print(f"Saved to: {output_dir}")


if __name__ == "__main__":
    create_split()
