
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main():
    tables_dir = PROJECT_ROOT / "results" / "tables"

    files = [
        "popularity_metrics.csv",
        "content_based_metrics.csv",
        "svd_metrics.csv",
        "als_metrics.csv",
    ]

    results = [
        pd.read_csv(tables_dir / filename)
        for filename in files
    ]

    comparison = pd.concat(results, ignore_index=True)

    columns = [
        "model",
        "evaluated_users",
        "precision@10",
        "recall@10",
        "map@10",
        "ndcg@10",
        "catalog_coverage",
    ]

    comparison = comparison[columns]

    comparison.to_csv(
        tables_dir / "model_comparison.csv",
        index=False
    )

    print("=== FINAL MODEL COMPARISON ===")
    print(comparison.to_string(index=False))
    print("\nSaved:", tables_dir / "model_comparison.csv")


if __name__ == "__main__":
    main()
