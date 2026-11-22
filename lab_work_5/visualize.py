import matplotlib
matplotlib.use("Agg")  # чтобы работало без GUI

import matplotlib.pyplot as plt
import seaborn as sns


def plot_top_words(model, feature_names, n_top_words, title, output_path):
    """Визуализация топ-слов каждого топика (слайд 20)."""
    n_topics = model.n_components
    n_cols = 5
    n_rows = (n_topics + n_cols - 1) // n_cols

    fig, axes = plt.subplots(
        n_rows, n_cols,
        figsize=(5 * n_cols, 4 * n_rows),
        sharex=False,
    )
    axes = axes.flatten()

    for topic_idx, topic in enumerate(model.components_):
        top_ind = topic.argsort()[:-n_top_words - 1:-1]
        top_words = [feature_names[i] for i in top_ind]
        weights = topic[top_ind]

        ax = axes[topic_idx]
        ax.barh(top_words, weights, height=0.7, color="teal")
        ax.set_title(f"Топик {topic_idx + 1}", fontdict={"fontsize": 14})
        ax.invert_yaxis()
        ax.tick_params(axis="y", labelsize=10)

    for i in range(n_topics, len(axes)):
        axes[i].axis("off")

    plt.subplots_adjust(top=0.92, bottom=0.05, wspace=0.9, hspace=0.5)
    plt.suptitle(title, fontsize=20)
    plt.savefig(output_path, bbox_inches="tight", dpi=110)
    plt.close()
    print(f"  Сохранено: {output_path}")


def plot_coherence(k_values, scores, best_k, title, output_path):
    """График выбора K по Coherence (слайд 16)."""
    plt.figure(figsize=(10, 6))
    plt.plot(k_values, scores, marker="o", linewidth=2)
    plt.axvline(best_k, color="red", linestyle="--", label=f"Оптимум K={best_k}")
    plt.title(title, fontsize=14)
    plt.xlabel("Число топиков K")
    plt.ylabel("Coherence Score (c_v)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(output_path, bbox_inches="tight", dpi=110)
    plt.close()
    print(f"  Сохранено: {output_path}")


def plot_doc_topic_heatmap(model, vec, texts, title, output_path):
    """Матрица документ-топик (слайд 12)."""
    X = vec.transform(texts)
    doc_topic = model.transform(X)

    sample_size = min(20, len(texts))
    plt.figure(figsize=(12, 8))
    sns.heatmap(
        doc_topic[:sample_size],
        cmap="YlGnBu",
        cbar=True,
        xticklabels=[f"T{i+1}" for i in range(model.n_components)],
    )
    plt.title(f"{title}: распределение тем (первые {sample_size} док.)", fontsize=14)
    plt.xlabel("Топики")
    plt.ylabel("Документы")
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", dpi=110)
    plt.close()
    print(f"  Сохранено: {output_path}")