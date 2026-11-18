import requests
from urllib.parse import quote
from urllib.parse import urlsplit, urlunsplit
from pathlib import Path
from datetime import date


class POTDError(Exception):
    """Ошибка получения Picture of the Day."""
    pass


class PictureOfTheDayCollector:
    API_URL = "https://commons.wikimedia.org/w/api.php"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "WikimediaLab3/1.0 "
                "(Educational project; contact: student@example.com)"
            )
        })

    def get_picture(self) -> dict:
        """Получает информацию о Picture of the Day."""

        today = date.today().strftime("%Y-%m-%d")

        params = {
            "action": "query",
            "format": "json",
            "titles": f"Template:Potd/{today}",
            "prop": "images",
            "imlimit": 1
        }

        try:
            response = self.session.get(
                self.API_URL,
                params=params,
                timeout=20
            )
            response.raise_for_status()

            data = response.json()

        except requests.RequestException as error:
            raise POTDError(
                f"Ошибка обращения к Wikimedia Commons: {error}"
            ) from error

        except ValueError as error:
            raise POTDError(
                "Wikimedia Commons вернул некорректный JSON."
            ) from error

        pages = data.get("query", {}).get("pages", {})

        for page in pages.values():
            images = page.get("images", [])

            if images:
                image_title = images[0]["title"]
                return self._get_image_info(image_title)

        raise POTDError(
            "Не удалось найти Picture of the Day за сегодня."
        )

    def _get_image_info(self, image_title: str) -> dict:
        """Получает URL изображения и его описание."""

        params = {
            "action": "query",
            "format": "json",
            "titles": image_title,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 960
        }

        try:
            response = self.session.get(
                self.API_URL,
                params=params,
                timeout=20
            )
            response.raise_for_status()
            data = response.json()

        except requests.RequestException as error:
            raise POTDError(
                f"Ошибка получения информации об изображении: {error}"
            ) from error

        except ValueError as error:
            raise POTDError(
                "Получен некорректный JSON с информацией об изображении."
            ) from error

        pages = data.get("query", {}).get("pages", {})

        for page in pages.values():
            imageinfo = page.get("imageinfo", [])

            if not imageinfo:
                continue

            info = imageinfo[0]
            metadata = info.get("extmetadata", {})

            description = (
                metadata.get("ImageDescription", {}).get("value", "")
            )

            return {
                "title": image_title,
                "image_url": info.get("thumburl", info.get("url", "")),
                "original_url": info.get("url", ""),
                "description": description,
                "author": metadata.get("Artist", {}).get("value", ""),
                "license": metadata.get("LicenseShortName", {}).get("value", ""),
                "file_page": info.get("descriptionurl", "")
            }

        raise POTDError(
            "Не удалось получить информацию об изображении."
        )

    def save_picture(
        self,
        picture: dict,
        output_dir: str = "output/potd"
    ) -> None:
        """Сохраняет изображение и описание в текстовый файл."""

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Получаем URL изображения из ответа API
        image_url = picture.get("image_url")

        if not image_url:
            raise POTDError("Отсутствует URL изображения.")

        # Скачиваем изображение
        try:
            response = self.session.get(
                image_url,
                timeout=30
            )

            response.raise_for_status()

            content_type = response.headers.get(
                "Content-Type", ""
            )

            if not content_type.startswith("image/"):
                raise POTDError(
                    f"Сервер вернул не изображение: {content_type}"
                )

            response_content = response.content

        except requests.RequestException as error:
            raise POTDError(
                f"Ошибка скачивания изображения: {error}"
            ) from error

        # Определяем расширение файла
        filename = picture.get("title", "")
        extension = Path(filename).suffix or ".jpg"

        base_name = "picture_of_the_day"

        image_path = output_path / f"{base_name}{extension}"
        text_path = output_path / f"{base_name}.txt"

        # Сохраняем изображение и описание
        try:
            image_path.write_bytes(response_content)

            description = picture.get(
                "description",
                "Описание отсутствует."
            )

            text_content = (
                f"Picture of the Day\n"
                f"Дата: {date.today()}\n"
                f"Название: {picture.get('title', '')}\n"
                f"Описание: {description}\n"
                f"Автор: {picture.get('author', '')}\n"
                f"Лицензия: {picture.get('license', '')}\n"
                f"Страница изображения: {picture.get('file_page', '')}\n"
                f"URL изображения: {image_url}\n"
            )

            text_path.write_text(
                text_content,
                encoding="utf-8"
            )

        except OSError as error:
            raise POTDError(
                f"Ошибка сохранения файлов POTD: {error}"
            ) from error

        print(f"[УСПЕХ] Изображение сохранено: {image_path}")
        print(f"[УСПЕХ] Описание сохранено: {text_path}")
