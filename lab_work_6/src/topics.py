import json
import re
from collections import Counter
from pathlib import Path

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.metrics import silhouette_score


RU_STOP_WORDS = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со",
    "как", "а", "то", "все", "она", "так", "его", "но", "да",
    "ты", "к", "у", "же", "вы", "за", "бы", "по", "только",
    "ее", "мне", "было", "вот", "от", "меня", "еще", "нет",
    "о", "из", "ему", "теперь", "когда", "даже", "ну", "ли",
    "если", "уже", "или", "ни", "быть", "был", "была", "были",
    "есть", "для", "до", "при", "мы", "они", "это", "этот",
    "эта", "этого", "себя", "там", "здесь", "где", "под",
    "над", "после", "перед", "между", "очень", "всего",
    "может", "будет", "будут", "чтобы", "также", "сейчас",
    "который", "которая", "которые", "которое", "свой",
    "свои", "своего", "него", "ней", "них", "ним", "ними",
    "сам", "самый", "один", "одна", "одно", "два", "три",
    "сегодня", "здесь", "прямо", "сейчас", "вместе",
}

CUSTOM_STOP_WORDS = set(ENGLISH_STOP_WORDS) | RU_STOP_WORDS

SPORT_OBJECTS = {
    "sports ball", "tennis racket", "skis", "snowboard",
    "surfboard", "baseball bat", "baseball glove",
    "skateboard", "frisbee",
}

MUSIC_LABELS = [
    "спокойная музыка", "тревожная музыка", "динамичная музыка",
    "печальная музыка", "веселая музыка", "лирическая музыка",
    "полицейская музыка", "напряженная музыка",
    "dramatic music", "background music", "upbeat music",
    "suspenseful music", "music",
]

def clean_metadata(text):
    text = str(text or "").lower()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"#[\wа-яё]+", " ", text)
    text = re.sub(r"\b(subscribe|follow|like|telegram|youtube|facebook|twitter)\b", " ", text)
    text = re.sub(r"[^a-zа-яё0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def get_transcript_text(video):
    transcript = video.get("transcript") or {}

    if isinstance(transcript, str):
        text = transcript
    elif isinstance(transcript, dict):
        text = transcript.get("text", "")
        if not text:
            text = " ".join(
                str(segment.get("text", ""))
                for segment in transcript.get("segments", [])
                if isinstance(segment, dict)
            )
    else:
        text = ""

    text = str(text).lower()

    # Удаляем типовые музыкальные подписи Whisper.
    music_count = 0
    for label in MUSIC_LABELS:
        count = len(re.findall(re.escape(label), text))
        music_count += count
        text = re.sub(re.escape(label), " ", text)

    words = re.findall(r"[a-zа-яё]{2,}", text)

    # Если распознавание в основном состоит из музыкальных подписей,
    # не используем его для тематической классификации.
    if music_count >= 5 or len(words) < 10:
        return ""

    # Не допускаем преобладания случайных символов и смешанных скриптов.
    valid_words = [
        word for word in words
        if re.fullmatch(r"[а-яё]+|[a-z]+", word)
    ]

    if len(valid_words) < 10:
        return ""

    return " ".join(valid_words)


def get_visual_objects(video):
    counts = Counter()

    for detection in video.get("detections", []):
        for obj in detection.get("objects", []):
            if not isinstance(obj, dict):
                continue

            name = str(obj.get("class_name", "")).lower()
            if name in SPORT_OBJECTS:
                counts[name] += 1

    return counts


def build_document(video):
    metadata = video.get("source_metadata") or {}

    title = clean_metadata(metadata.get("title", ""))
    description = clean_metadata(metadata.get("description", ""))
    discipline = clean_metadata(metadata.get("discipline", ""))

    tags = metadata.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]

    tags_text = clean_metadata(" ".join(map(str, tags)))
    transcript = get_transcript_text(video)
    objects = get_visual_objects(video)

    # Название и дисциплина задают контекст.
    # Транскрипт добавляет содержательные признаки.
    parts = [
        title,
        title,
        discipline,
        tags_text,
        transcript[:6000],
        description[:500],
        " ".join(name.replace(" ", "") for name, _ in objects.most_common(5)),
    ]

    document = " ".join(parts)
    return re.sub(r"\s+", " ", document).strip()


def cluster_videos(videos, n_clusters=3):
    if len(videos) < n_clusters + 1:
        raise ValueError("Для кластеризации недостаточно видео")

    documents = [build_document(video) for video in videos]

    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        min_df=1,
        max_df=1.0,
        sublinear_tf=True,
        stop_words=list(CUSTOM_STOP_WORDS),
        token_pattern=r"(?u)\b\w\w+\b",
    )

    matrix = vectorizer.fit_transform(documents)

    model = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=30,
    )

    labels = model.fit_predict(matrix)
    terms = vectorizer.get_feature_names_out()

    keywords = {}

    for cluster_id, center in enumerate(model.cluster_centers_):
        indices = center.argsort()[::-1][:12]
        keywords[str(cluster_id)] = [
            str(terms[index]) for index in indices
        ]

    score = float(silhouette_score(matrix, labels))

    return labels, keywords, score


def run_clustering(input_dir: Path, output_path: Path, n_clusters=3):
    videos = []

    for path in sorted(input_dir.glob("*.json")):
        if path.name.startswith("topic_clusters"):
            continue

        data = json.loads(path.read_text(encoding="utf-8"))

        if data.get("status") not in ("completed", "completed_with_warnings"):
            continue

        metadata = data.get("source_metadata") or {}

        videos.append({
            "id": data.get("id") or path.stem,
            "title": metadata.get("title", path.stem),
            "discipline": metadata.get("discipline", ""),
            "data": data,
        })

    if len(videos) < n_clusters + 1:
        raise ValueError("Недостаточно видео для кластеризации")

    source_data = [video["data"] for video in videos]

    labels, keywords, score = cluster_videos(source_data, n_clusters)

    results = []

    for video, label in zip(videos, labels):
        cluster_id = int(label)
        results.append({
            "id": video["id"],
            "title": video["title"],
            "discipline": video["discipline"],
            "cluster": cluster_id,
            "keywords": keywords[str(cluster_id)],
        })

    quality = []

    for k in range(2, min(5, len(videos))):
        _, _, k_score = cluster_videos(source_data, k)
        quality.append({
            "n_clusters": k,
            "silhouette": round(k_score, 4),
        })

    output = {
        "method": "TF-IDF + KMeans",
        "n_videos": len(videos),
        "n_clusters": n_clusters,
        "silhouette": round(score, 4),
        "cluster_sizes": dict(Counter(item["cluster"] for item in results)),
        "cluster_keywords": keywords,
        "quality_comparison": quality,
        "videos": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output
