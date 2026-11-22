import argparse
import json
import os
from pathlib import Path

from preprocess import load_and_prepare_data
from model import train_model, find_best_k
from visualize import plot_top_words, plot_coherence, plot_doc_topic_heatmap


def save_topics(model, feature_names, output_path, n_top_words=10):
    """Сохраняет топ-слова по топикам в JSON."""
    result = {"topics": []}
    for i, topic in enumerate(model.components_):
        top_ind = topic.argsort()[:-n_top_words - 1:-1]
        words = [
            {"word": feature_names[j], "weight": round(float(topic[j]), 4)}
            for j in top_ind
        ]
        result["topics"].append({"topic_id": i + 1, "words": words})

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  Сохранено: {output_path}")


def resolve_news_path():
    for p in ["data/news.csv", "data/news.json"]:
        if Path(p).exists():
            return p
    raise FileNotFoundError("Нет ни data/news.csv, ни data/news.json")


def main():
    parser = argparse.ArgumentParser(description="Lab 5: Topic Modeling")
    parser.add_argument("--dataset", choices=["news", "products"], required=True)
    parser.add_argument("--method", choices=["lda", "nmf", "both"], default="lda")
    parser.add_argument("--topics", default="10", help="Число топиков (число или 'auto')")
    parser.add_argument("--min-k", type=int, default=3,
                    help="Минимальное K при --topics auto (по умолчанию 3)")
    parser.add_argument("--max-k", type=int, default=20,
                        help="Максимальное K при --topics auto (по умолчанию 20)")
    parser.add_argument("--compare", action="store_true", help="Сравнить LDA и NMF")
    parser.add_argument("--output", required=True, help="Префикс для выходных файлов")
    args = parser.parse_args()

    os.makedirs("output", exist_ok=True)
    output_prefix = f"output/{args.output}"

    # 1. Загрузка данных
    if args.dataset == "news":
        texts, tokenized = load_and_prepare_data(
            resolve_news_path(), ["title", "summary"]
        )
    else:
        texts, tokenized = load_and_prepare_data(
            "data/products.csv", ["name", "description", "longDescription"]
        )

    print(f"Загружено документов: {len(texts)}")
    if len(texts) < 50:
        print("⚠️ Мало документов, проверьте данные!")

    # 2. Определяем методы
    methods = ["lda", "nmf"] if (args.method == "both" or args.compare) else [args.method]
    results = {}

    for method in methods:
        print(f"\n=== {method.upper()} ===")

        # Определяем K
        if args.topics == "auto":
            best_k, k_vals, scores = find_best_k(texts, tokenized, method, min_k=args.min_k, max_k=args.max_k)
            plot_coherence(
                k_vals, scores, best_k,
                f"Выбор K ({method.upper()})",
                f"{output_prefix}_{method}_coherence.png",
            )
            n_topics = best_k
            print(f"Оптимальное K = {best_k} (диапазон {args.min_k}..{args.max_k})")
        else:
            n_topics = int(args.topics)

        # Обучение
        model, vec, features, coh = train_model(texts, tokenized, method, n_topics)
        results[method] = coh
        print(f"Coherence Score: {coh:.4f}")

        # Визуализация и сохранение
        plot_top_words(
            model, features, 10,
            f"{method.upper()} (K={n_topics})",
            f"{output_prefix}_{method}_words.png",
        )
        plot_doc_topic_heatmap(
            model, vec, texts,
            f"{method.upper()}",
            f"{output_prefix}_{method}_heatmap.png",
        )
        save_topics(model, features, f"{output_prefix}_{method}_topics.json")

    # Сравнение
    if len(results) > 1:
        print("\n=== СРАВНЕНИЕ ===")
        for m, c in results.items():
            print(f"{m.upper()}: Coherence = {c:.4f}")
        with open(f"{output_prefix}_comparison.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()