import argparse
import json
from pathlib import Path
import webbrowser

import requests

from collectors.wikipedia import WikipediaCollector
from collectors.exceptions import WikimediaError
from collectors.commons import CommonsCollector, CommonsError
from storage import save_json, load_json, StorageError
from graph import build_graph, GraphError


def main():

    parser = argparse.ArgumentParser(
        description="Wikimedia Data Collector"
    )

    parser.add_argument(
        "query",
        type=str,
        help="Запрос о предметной области"
    )

    parser.add_argument(
        "--language",
        type=str,
        default="ru",
        choices=["ru", "en", "de", "fr"],
        help="Язык Википедии (по умолчанию: ru)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Максимальное количество статей"
    )

    parser.add_argument(
        "--images-limit",
        type=int,
        default=3,
        help="Количество изображений для каждой статьи (по умолчанию: 3)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="output/articles.json",
        help="Путь сохранения JSON"
    )

    parser.add_argument(
        "--show",
        type=bool,
        default=False,
        help="Показать построенный граф"
    )

    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit должен быть не меньше 1")
    if args.images_limit < 1:
        parser.error("--images-limit должен быть не меньше 1")

    print("=" * 50)
    print("WIKIMEDIA DATA COLLECTOR")
    print("=" * 50)

    print(f"Запрос: {args.query}")
    print(f"Язык: {args.language}")
    print(f"Лимит статей: {args.limit}")

    try:
        collector = WikipediaCollector(
            language=args.language
        )

        articles = collector.collect_articles(
            query=args.query,
            max_articles=args.limit
        )

        if not articles:
            print(
                "\n[РЕЗУЛЬТАТ] Не удалось собрать статьи."
            )
            return

        try:
            save_json(articles, args.output)

        except OSError as error:
            print(
                f"\n[ОШИБКА СОХРАНЕНИЯ] "
                f"Не удалось сохранить файл: {error}"
            )
            return
        except StorageError as error:
            print(f"[ОШИБКА ЗАГРУЗКИ] {error}")

        try:
            print("\n" + "=" * 50)
            print("СБОР ИЗОБРАЖЕНИЙ WIKIMEDIA COMMONS")
            print("=" * 50)

            commons = CommonsCollector()

            images = commons.collect_for_articles(
                articles=articles,
                images_per_article=args.images_limit
            )

            commons.save_images(
                images,
                filepath="output/images.json"
            )

        except CommonsError as error:
            print(f"\n[ОШИБКА COMMONS] {error}")

        try:
            build_graph(
                articles,
                filepath="output/graph.html"
            )
            if args.show:
                graph_path = Path(args.output).resolve().parent / "graph.html"
                if graph_path.exists():
                    webbrowser.open(graph_path.as_uri())
                else:
                    print(f"[ОШИБКА] Файл графа не найден: {graph_path}")

        except GraphError as error:
            print(f"[ОШИБКА ГРАФА] {error}")

        print("\n" + "=" * 50)
        print("РЕЗУЛЬТАТ СБОРА")
        print("=" * 50)

        print(f"Собрано статей: {len(articles)}")
        print(f"Запрошено статей: {args.limit}")

        if len(articles) < args.limit:
            print(
                "[ПРЕДУПРЕЖДЕНИЕ] "
                "Сбор завершён не полностью."
            )
        else:
            print("[УСПЕХ] Необходимое количество статей собрано.")

    except WikimediaError as error:
        print(f"\n[ОШИБКА WIKIMEDIA] {error}")

    except KeyboardInterrupt:
        print("\n[ОТМЕНА] Сбор прерван пользователем.")

    except requests.exceptions.RequestException:
        print(
            "\n[ОШИБКА] Не удалось выполнить сетевой запрос."
        )

    except Exception as error:
        print(
            f"\n[НЕПРЕДВИДЕННАЯ ОШИБКА] {error}"
        )
        print(
            "Если проблема повторяется, "
            "проверьте настройки приложения."
        )


if __name__ == "__main__":
    main()
