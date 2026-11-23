from pathlib import Path

from src.topics import run_clustering

ROOT = Path(__file__).resolve().parents[1]

result = run_clustering(
    input_dir=ROOT / "data" / "processed_v2",
    output_path=ROOT / "data" / "processed_v2" / "topic_clusters.json",
    n_clusters=3,
)

print("\nТЕМАТИЧЕСКАЯ КЛАСТЕРИЗАЦИЯ")
print(f"Метод: {result['method']}")
print(f"Видео: {result['n_videos']}")
print(f"Кластеров: {result['n_clusters']}")
print(f"Silhouette score: {result['silhouette']}")

print("\nРАЗМЕРЫ КЛАСТЕРОВ")
for cluster, size in result["cluster_sizes"].items():
    print(f"Кластер {cluster}: {size} видео")

print("\nСОДЕРЖАНИЕ КЛАСТЕРОВ")
for cluster, keywords in result["cluster_keywords"].items():
    print(f"\nКластер {cluster}: {', '.join(keywords)}")

print("\nРАСПРЕДЕЛЕНИЕ ВИДЕО")
for video in result["videos"]:
    print(f"\n[{video['cluster']}] {video['title']}")
    print(f"    Вид спорта: {video['discipline']}")
    print(f"    Ключевые слова: {', '.join(video['keywords'])}")

print("\nСРАВНЕНИЕ ЧИСЛА КЛАСТЕРОВ")
for item in result["quality_comparison"]:
    if "silhouette" in item:
        print(
            f"k={item['n_clusters']}: "
            f"silhouette={item['silhouette']}"
        )
    else:
        print(f"k={item['n_clusters']}: {item['error']}")

print("\nРезультат: data/processed_v2/topic_clusters.json")
