
import json
from pathlib import Path
from datetime import datetime, timezone

from models.article import Article


class StorageError(Exception):
    """Ошибка при работе с хранилищем данных."""
    pass


def save_json(articles: list[Article], filepath: str) -> None:
    """
    Сохраняет список статей в JSON.

    Args:
        articles: Список объектов Article.
        filepath: Путь к выходному JSON-файлу.
    """

    path = Path(filepath)

    try:
        # Создаём родительскую директорию, если её нет
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "metadata": {
                "total_articles": len(articles),
                "exported_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "format_version": "1.0"
            },
            "articles": [
                article.to_dict()
                for article in articles
            ]
        }

        # Сохраняем данные в JSON
        with path.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4
            )

        print(f"[УСПЕХ] Данные сохранены: {path.resolve()}")

    except (OSError, TypeError, ValueError) as error:
        raise StorageError(
            f"Не удалось сохранить JSON: {error}"
        ) from error


def load_json(filepath: str) -> list[Article]:
    """
    Загружает статьи из JSON.

    Args:
        filepath: Путь к JSON-файлу.

    Returns:
        Список объектов Article.
    """

    path = Path(filepath)

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise StorageError(
                "Некорректная структура JSON: ожидался объект."
            )

        raw_articles = data.get("articles")

        if not isinstance(raw_articles, list):
            raise StorageError(
                "В JSON отсутствует список articles."
            )

        articles = []

        for index, item in enumerate(raw_articles):
            try:
                article = Article(
                    title=item["title"],
                    language=item["language"],
                    url=item["url"],
                    text=item["text"],
                    links=item["links"]
                )
                articles.append(article)

            except (KeyError, TypeError) as error:
                raise StorageError(
                    f"Некорректная статья под номером {index}: {error}"
                ) from error

        return articles

    except FileNotFoundError as error:
        raise StorageError(
            f"Файл не найден: {path}"
        ) from error

    except json.JSONDecodeError as error:
        raise StorageError(
            f"Файл содержит некорректный JSON: {error}"
        ) from error

    except OSError as error:
        raise StorageError(
            f"Ошибка чтения файла: {error}"
        ) from error
