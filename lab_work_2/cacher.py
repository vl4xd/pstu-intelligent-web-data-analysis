import json
from pathlib import Path
from typing import Any


class JsonPageCache:

    def __init__(self, cache_path: str | Path):
        self.cache_path = Path(cache_path)
        self.pages: dict[str, dict[str, Any]] = {}

        self.load()

    def load(self) -> None:
        """Загружает кэш из JSON."""
        if not self.cache_path.exists():
            return
        try:
            with open(self.cache_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            self.pages = data.get("pages", {})
        except (json.JSONDecodeError, OSError) as error:
            print(f"Не удалось загрузить кэш: {error}")
            self.pages = {}

    def get(self, url: str) -> dict | None:
        """Возвращает данные страницы из кэша."""
        return self.pages.get(url)

    def set(self, url: str, page_data: dict) -> None:
        """Добавляет или обновляет страницу в кэше."""
        self.pages[url] = page_data

    def save(self) -> None:
        """Сохраняет кэш в JSON."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "pages": self.pages
        }
        temp_path = self.cache_path.with_suffix(".json.tmp")

        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4
            )

        temp_path.replace(self.cache_path)