import json
import html
from pathlib import Path

import gradio as gr
import pandas as pd

from src.config import RAW_DIR, PROCESSED_DIR
from src.add_video import add_video_to_catalog


def load_dataset():
    videos = {}

    for path in PROCESSED_DIR.glob("*.json"):
        if path.name == "topic_clusters.json":
            continue

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            video_id = data["id"]
            metadata = data.get("source_metadata", {})

            raw_files = list(RAW_DIR.glob(f"{video_id}.*"))
            video_path = next(
                (str(f) for f in raw_files
                 if f.suffix.lower() in {".mp4", ".mkv", ".webm", ".avi"}),
                None,
            )

            videos[video_id] = {
                "data": data,
                "title": metadata.get("title", video_id),
                "discipline": metadata.get("discipline", "не указана"),
                "duration": float(metadata.get("duration_seconds", 0) or 0),
                "video_path": video_path,
            }
        except Exception as exc:
            print(f"Ошибка загрузки {path.name}: {exc}")

    return videos


VIDEOS = load_dataset()


def format_time(seconds):
    seconds = max(0, int(float(seconds or 0)))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def get_objects(data):
    counts = {}
    for frame in data.get("detections", []):
        for obj in frame.get("objects", []):
            name = obj.get("class_name", "unknown")
            counts[name] = counts.get(name, 0) + 1
    return counts


def get_timeline(data):
    rows = []

    for event in data.get("events", []):
        start = float(event.get("start", 0) or 0)
        end = float(event.get("end", start) or start)

        rows.append({
            "Время": format_time(start),
            "Секунды": round(start, 2),
            "Тип": str(event.get("type", "event")),
            "Событие": str(event.get("label", "Событие")),
            "Описание": str(
                event.get("text", event.get("class_name", ""))
            )[:220],
            "Конец": format_time(end),
        })

    for scene in data.get("scene_changes", []):
        timestamp = float(scene.get("time", 0) or 0)
        rows.append({
            "Время": format_time(timestamp),
            "Секунды": round(timestamp, 2),
            "Тип": "scene_change",
            "Событие": "Смена сцены",
            "Описание": f"Изменение изображения, score: {scene.get('score', '')}",
            "Конец": format_time(timestamp),
        })

    rows.sort(key=lambda row: row["Секунды"])

    return pd.DataFrame(rows, columns=[
        "Время", "Секунды", "Тип", "Событие", "Описание", "Конец"
    ])


def get_video_stats(video_id):
    item = VIDEOS[video_id]
    data = item["data"]

    objects = get_objects(data)
    transcript = data.get("transcript", {})
    transcript_text = transcript.get("text", "") if isinstance(transcript, dict) else ""

    stats = (
        f"**Дисциплина:** {item['discipline']}  \n"
        f"**Длительность:** {format_time(item['duration'])}  \n"
        f"**Проанализировано кадров:** {len(data.get('frames', []))}  \n"
        f"**Кадров с детекциями:** {len(data.get('detections', []))}  \n"
        f"**Обнаружений объектов:** {sum(objects.values())}  \n"
        f"**Символов транскрипта:** {len(transcript_text)}  \n"
        f"**Аудиоинтервалов:** {len(data.get('audio_features', []))}  \n"
        f"**Смен сцен:** {len(data.get('scene_changes', []))}  \n"
        f"**Событий:** {len(data.get('events', []))}  \n"
        f"**Статус:** {data.get('status', 'неизвестен')}"
    )

    top_objects = sorted(
        objects.items(), key=lambda item: item[1], reverse=True
    )[:10]

    object_text = "\n".join(
        f"- **{name}** — {count}" for name, count in top_objects
    ) or "Объекты не обнаружены."

    return stats, object_text


def search_videos(query):
    query = (query or "").strip().lower()
    results = []

    for video_id, item in VIDEOS.items():
        data = item["data"]
        transcript = data.get("transcript", {})
        transcript_text = transcript.get("text", "") if isinstance(transcript, dict) else ""
        objects = get_objects(data)

        searchable = " ".join([
            item["title"],
            item["discipline"],
            transcript_text,
            " ".join(objects.keys()),
            " ".join(str(e.get("text", "")) for e in data.get("events", [])),
        ]).lower()

        if not query or query in searchable:
            results.append({
                "Видео": item["title"],
                "Тема": item["discipline"],
                "Длительность": format_time(item["duration"]),
                "Объектов": sum(objects.values()),
                "ID": video_id,
            })

    return pd.DataFrame(results)


def load_video(video_id):
    if not video_id or video_id not in VIDEOS:
        return None, "<p>Видео не выбрано.</p>", "Нет данных.", "Нет данных."

    item = VIDEOS[video_id]
    data = item["data"]

    return (
        item["video_path"],
        render_timeline(data),
        *get_video_stats(video_id),
    )


def render_timeline(data):
    timeline = get_timeline(data)

    if timeline.empty:
        return "<p>События не найдены.</p>"

    rows = []
    for _, event in timeline.iterrows():
        seconds = float(event["Секунды"])
        description = html.escape(str(event["Описание"]))
        event_type = html.escape(str(event["Тип"]))
        label = html.escape(str(event["Событие"]))
        timestamp = html.escape(str(event["Время"]))

        rows.append(
            f'<tr>'
            f'<td><button type="button" '
            f'onclick="'
            f'const v=document.querySelector(\'#video-player video\');'
            f'if(v){{v.pause();v.currentTime={seconds};}}'
            f'" '
            f'style="cursor:pointer;padding:5px 10px;">'
            f'{timestamp}</button></td>'
            f'<td>{event_type}</td>'
            f'<td>{label}</td>'
            f'<td>{description}</td>'
            f'</tr>'
        )

    return (
        '<div style="max-height:500px;overflow-y:auto;">'
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead><tr>'
        '<th>Переход</th><th>Тип</th><th>Событие</th><th>Описание</th>'
        '</tr></thead>'
        '<tbody>' + "".join(rows) + '</tbody>'
        '</table></div>'
    )


def topic_distribution():
    counts = {}
    for item in VIDEOS.values():
        topic = item["discipline"]
        counts[topic] = counts.get(topic, 0) + 1

    return "\n".join(
        f"- **{topic.capitalize()}**: {count} видео"
        for topic, count in sorted(counts.items())
    )


def seek_to_event(evt: gr.SelectData):
    try:
        row_index = evt.index[0] if isinstance(evt.index, (tuple, list)) else evt.index
        return float(current_timeline.iloc[row_index]["Секунды"])
    except Exception:
        return 0.0


current_timeline = pd.DataFrame()


def update_timeline(video_id):
    global current_timeline
    if video_id not in VIDEOS:
        current_timeline = pd.DataFrame()
        return current_timeline

    current_timeline = get_timeline(VIDEOS[video_id]["data"])
    return current_timeline


def select_event(evt: gr.SelectData, video_id):
    try:
        row_index = evt.index[0] if isinstance(evt.index, (tuple, list)) else evt.index
        timeline = get_timeline(VIDEOS[video_id]["data"])
        return float(timeline.iloc[row_index]["Секунды"])
    except Exception:
        return 0.0


def add_video_ui(url, discipline, progress=gr.Progress(track_tqdm=True)):
    try:
        return add_video_to_catalog(url, discipline, progress)
    except Exception as exc:
        return f"**Ошибка добавления видео:** {html.escape(str(exc))}", None


def refresh_catalog(video_id):
    global VIDEOS

    if not video_id:
        return (
            gr.update(), None, gr.update(), gr.update(),
            gr.update(), gr.update(), gr.update()
        )

    VIDEOS = load_dataset()

    if video_id not in VIDEOS:
        return (
            gr.update(), None, gr.update(), gr.update(),
            gr.update(), gr.update(), gr.update()
        )

    choices = [
        (f"{v['discipline'].capitalize()} — {v['title'][:75]}", key)
        for key, v in VIDEOS.items()
    ]

    return (
        gr.update(choices=choices, value=video_id),
        *load_video(video_id),
        search_videos(""),
        topic_distribution(),
    )


with gr.Blocks(title="Интеллектуальный анализ видеоданных") as demo:
    gr.Markdown(
        """
        # Система интеллектуального анализа видеоданных

        Поиск по спортивным видео, распознанной речи, объектам и временным событиям.
        """
    )

    gr.Markdown("## Добавление нового видео")

    with gr.Row():
        with gr.Column(scale=3):
            new_video_url = gr.Textbox(
                label="Ссылка на видео",
                placeholder="Вставьте ссылку на Rutube или другой поддерживаемый источник",
            )
        with gr.Column(scale=1):
            new_video_discipline = gr.Dropdown(
                choices=[
                    "футбол",
                    "баскетбол",
                    "теннис",
                    "лёгкая атлетика",
                    "хоккей",
                    "другое",
                ],
                value="футбол",
                label="Дисциплина",
                allow_custom_value=True,
            )

    add_video_button = gr.Button(
        "Добавить и проанализировать",
        variant="primary",
    )
    add_video_status = gr.Markdown()
    new_video_id = gr.State(None)

    with gr.Row():
        search_input = gr.Textbox(
            label="Поиск по видео",
            placeholder="Например: Sharapova, Ronaldo, person, баскетбол...",
            scale=4,
        )
        search_button = gr.Button("Найти", variant="primary")

    search_results = gr.Dataframe(
        value=search_videos(""),
        label="Результаты поиска",
        interactive=False,
        wrap=True,
    )

    video_choices = [
        (f"{v['discipline'].capitalize()} — {v['title'][:75]}", k)
        for k, v in VIDEOS.items()
    ]

    video_select = gr.Dropdown(
        choices=video_choices,
        value=next(iter(VIDEOS), None),
        label="Выберите видео",
        interactive=True,
    )

    with gr.Row():
        with gr.Column(scale=3):
            video_player = gr.Video(
                label="Видеоплеер",
                elem_id="video-player",
                height=420,
            )

        with gr.Column(scale=2):
            stats_output = gr.Markdown()
            objects_output = gr.Markdown()

    gr.Markdown("## Временная шкала событий")
    gr.Markdown(
        "Нажмите на строку события — видео автоматически перейдёт "
        "к соответствующей временной метке."
    )

    timeline_table = gr.HTML(
        value="<p>Выберите видео.</p>",
        label="Временная шкала событий",
    )


    gr.Markdown("## Тематическое распределение коллекции")
    topics_output = gr.Markdown(topic_distribution())

    add_video_button.click(
        fn=add_video_ui,
        inputs=[new_video_url, new_video_discipline],
        outputs=[add_video_status, new_video_id],
        show_progress="full",
    ).then(
        fn=refresh_catalog,
        inputs=new_video_id,
        outputs=[
            video_select,
            video_player,
            timeline_table,
            stats_output,
            objects_output,
            search_results,
            topics_output,
        ],
    )

    search_button.click(
        fn=search_videos,
        inputs=search_input,
        outputs=search_results,
    )

    search_input.submit(
        fn=search_videos,
        inputs=search_input,
        outputs=search_results,
    )

    video_select.change(
        fn=load_video,
        inputs=video_select,
        outputs=[
            video_player,
            timeline_table,
            stats_output,
            objects_output,
        ],
    )



    demo.load(
        fn=load_video,
        inputs=video_select,
        outputs=[
            video_player,
            timeline_table,
            stats_output,
            objects_output,
        ],
    )


if __name__ == "__main__":
    if not VIDEOS:
        raise RuntimeError("Не найдены обработанные видео в data/processed_v2")

    print(f"Загружено видео: {len(VIDEOS)}")
    demo.launch()
