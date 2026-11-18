
import time
import requests

from pathlib import Path


class CommonsError(Exception):
    """Базовая ошибка Wikimedia Commons."""
    pass


class CommonsCollector:
    """Сбор изображений из Wikimedia Commons."""

    API_URL = "https://commons.wikimedia.org/w/api.php"

    def __init__(self, delay: float = 1.2):
        self.delay = delay
        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "WikimediaLab3/1.0 "
                "(Educational project; contact: your-email@example.com)"
            )
        })

    def _request(self, params: dict) -> dict:
        """Выполняет запрос к Wikimedia Commons API."""

        params.update({
            "format": "json",
            "formatversion": 2
        })

        for attempt in range(5):

            try:
                response = self.session.get(
                    self.API_URL,
                    params=params,
                    timeout=(10, 30)
                )

                if response.status_code == 429:
                    wait = min(5 * (2 ** attempt), 60)

                    if attempt == 4:
                        raise CommonsError(
                            "Превышен лимит запросов Wikimedia Commons."
                        )

                    print(
                        f"[ПРЕДУПРЕЖДЕНИЕ] HTTP 429. "
                        f"Повтор через {wait} секунд."
                    )

                    time.sleep(wait)
                    continue

                if response.status_code in (500, 502, 503, 504):

                    if attempt == 4:
                        raise CommonsError(
                            "Сервер Wikimedia Commons недоступен."
                        )

                    time.sleep(2 ** (attempt + 1))
                    continue

                response.raise_for_status()

                data = response.json()

                if "error" in data:
                    raise CommonsError(
                        f"Ошибка API: {data['error']}"
                    )

                return data

            except requests.exceptions.Timeout:
                if attempt == 4:
                    raise CommonsError(
                        "Превышено время ожидания ответа Commons."
                    )

                time.sleep(2 ** (attempt + 1))

            except requests.exceptions.ConnectionError:
                if attempt == 4:
                    raise CommonsError(
                        "Не удалось подключиться к Wikimedia Commons."
                    )

                time.sleep(2 ** (attempt + 1))

            except requests.exceptions.RequestException as error:
                raise CommonsError(
                    f"Ошибка HTTP-запроса: {error}"
                ) from error

        raise CommonsError(
            "Не удалось выполнить запрос к Wikimedia Commons."
        )

    def search_images(
        self,
        query: str,
        limit: int = 3
    ) -> list[dict]:
        """Ищет изображения по названию статьи."""

        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}",
            "gsrnamespace": 6,
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 800
        }

        data = self._request(params)

        pages = data.get("query", {}).get("pages", [])

        images = []

        for page in pages:

            image_info = page.get("imageinfo", [])

            if not image_info:
                continue

            info = image_info[0]
            metadata = info.get("extmetadata", {})

            images.append({
                "title": page.get("title", ""),
                "image_url": info.get("thumburl", info.get("url", "")),
                "original_url": info.get("url", ""),
                "file_page": info.get("descriptionurl", ""),
                "description": metadata.get(
                    "ImageDescription", {}
                ).get("value", ""),
                "author": metadata.get(
                    "Artist", {}
                ).get("value", ""),
                "license": metadata.get(
                    "LicenseShortName", {}
                ).get("value", "")
            })

        time.sleep(self.delay)

        return images

    def collect_for_articles(
        self,
        articles: list,
        images_per_article: int = 3
    ) -> list[dict]:
        """Ищет изображения для каждой собранной статьи."""

        all_images = []

        for index, article in enumerate(articles, start=1):

            print(
                f"[{index}/{len(articles)}] "
                f"Поиск изображений: {article.title}"
            )

            try:
                images = self.search_images(
                    query=article.title,
                    limit=images_per_article
                )

                for image in images:
                    image["article_title"] = article.title
                    image["article_url"] = article.url

                all_images.extend(images)

                print(
                    f"  Найдено изображений: {len(images)}"
                )

            except CommonsError as error:
                print(
                    f"[ОШИБКА COMMONS] "
                    f"{article.title}: {error}"
                )

        return all_images

    def save_images(
        self,
        images: list[dict],
        filepath: str = "output/images.json"
    ) -> None:
        """Сохраняет изображения в JSON."""

        import json

        path = Path(filepath)

        try:
            path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            with path.open("w", encoding="utf-8") as file:
                json.dump(
                    images,
                    file,
                    ensure_ascii=False,
                    indent=4
                )

            print(
                f"[УСПЕХ] Сохранено изображений: "
                f"{len(images)}"
            )

        except (OSError, TypeError, ValueError) as error:
            raise CommonsError(
                f"Не удалось сохранить изображения: {error}"
            ) from error
