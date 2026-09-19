from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import requests


INDEX_API_BASE = "https://index.commoncrawl.org"
COLLECTIONS_URL = f"{INDEX_API_BASE}/collinfo.json"


class CdxError(RuntimeError):
    """Ошибка при работе с Common Crawl CDX API."""


@dataclass(frozen=True)
class CdxRecord:
    """Одна запись из CDX-индекса Common Crawl.

    Содержит URL, метку времени, тип содержимого, диапазон байт в WARC-файле
    и другую служебную информацию, необходимую для точечной загрузки capture.
    """

    url: str
    timestamp: str
    mime: str
    status: str
    length: int
    offset: int
    filename: str
    digest: str | None = None

    @property
    def archived_at(self) -> str:
        """Возвращает читаемую дату архивации из timestamp.

        Формат timestamp в CDX: YYYYMMDDhhmmss. Преобразует его
        в строку вида 'YYYY-MM-DD HH:MM:SS UTC'. Если длина timestamp
        не 14 символов, возвращает исходное значение без изменений.
        """

        if len(self.timestamp) != 14:
            return self.timestamp

        return (
            f"{self.timestamp[0:4]}-{self.timestamp[4:6]}-"
            f"{self.timestamp[6:8]} {self.timestamp[8:10]}:"
            f"{self.timestamp[10:12]}:{self.timestamp[12:14]} UTC"
        )


def normalize_domain(value: str) -> str:
    """Нормализует ввод вида https://example.com/path -> example.com."""
    value = value.strip()

    if not value:
        raise CdxError("Домен не может быть пустым.")

    value = re.sub(r"^https?://", "", value, flags=re.IGNORECASE)
    value = value.split("/", 1)[0].strip().rstrip(".")
    value = value.removeprefix("*.")

    if not value or "." not in value:
        raise CdxError(
            f"Некорректный домен: {value!r}. Пример: example.com"
        )

    return value


class CdxClient:
    """Клиент для работы с CDX API Common Crawl.

    Инкапсулирует HTTP-сессию, таймауты и парсинг ответов CDX-индекса.
    Позволяет получить список crawl-индексов и список HTML-кандидатов
    по заданному домену.
    """

    def __init__(
        self,
        timeout: float = 30.0,
        user_agent: str = "common-crawl-cli/1.0",
    ) -> None:
        """Создаёт HTTP-сессию с заданным таймаутом и User-Agent."""
        
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def close(self) -> None:
        """Закрывает HTTP-сессию и освобождает ресурсы."""

        self.session.close()

    def get_latest_crawl_id(self) -> str:
        """Возвращает id самого свежего индекса Common Crawl.

        Запрашивает collinfo.json и берёт идентификатор первой записи
        (индексы отсортированы от нового к старому). При сетевой ошибке
        или некорректном JSON бросает CdxError.
        """

        try:
            response = self.session.get(COLLECTIONS_URL, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise CdxError(
                f"Не удалось получить список индексов Common Crawl: {exc}"
            ) from exc
        except ValueError as exc:
            raise CdxError(
                "Common Crawl вернул некорректный JSON со списком индексов."
            ) from exc

        if not isinstance(payload, list) or not payload:
            raise CdxError("Список Common Crawl индексов пуст.")

        crawl_id = payload[0].get("id")
        if not crawl_id:
            raise CdxError("В записи последнего индекса отсутствует поле id.")

        return str(crawl_id)

    def query_html(
        self,
        crawl_id: str,
        domain: str,
        limit: int = 500,
    ) -> list[CdxRecord]:
        """Возвращает HTML-кандидатов из одного crawl.

        Делает запрос к CDX-индексу указанного crawl с фильтрами
        status:200 и mime:text/html, схлопывает дубликаты по urlkey
        и парсит NDJSON-ответ в список CdxRecord. При HTTP-ошибке
        (502/503/504 и т.п.) или ошибке парсинга бросает CdxError.
        """

        if not crawl_id or not re.fullmatch(r"CC-MAIN-\d{4}-\d{2}", crawl_id):
            raise CdxError(
                "Некорректный --crawl. Ожидался формат CC-MAIN-YYYY-WW."
            )

        normalized_domain = normalize_domain(domain)
        url = f"{INDEX_API_BASE}/{crawl_id}-index"

        params = [
            ("url", normalized_domain),
            ("matchType", "domain"),
            ("output", "json"),
            ("limit", str(limit)),
            # Сначала оставляем только успешные HTML-страницы.
            ("filter", "status:200"),
            ("filter", "mime:text/html"),
            # Для поиска по содержимому достаточно одной capture на URL.
            ("collapse", "urlkey"),
        ]

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 503:
                raise CdxError(
                    "Common Crawl CDX API вернул 503 (rate limit). "
                    "Увеличьте --delay и повторите позже."
                ) from exc

            if exc.response is not None:
                status = exc.response.status_code
                body = exc.response.text[:300].strip()
                raise CdxError(
                    f"Ошибка CDX API ({status}): {body}"
                ) from exc

            raise CdxError("Ошибка CDX API (нет ответа от сервера).") from exc
        except requests.RequestException as exc:
            raise CdxError(f"Ошибка сети при запросе CDX API: {exc}") from exc

        records: list[CdxRecord] = []
        for line_number, line in enumerate(
            response.text.splitlines(),
            start=1,
        ):
            if not line.strip():
                continue

            try:
                item: dict[str, Any] = response_to_dict(line)
            except ValueError as exc:
                raise CdxError(
                    f"Не удалось разобрать CDX JSON в строке {line_number}: {exc}"
                ) from exc

            try:
                records.append(
                    CdxRecord(
                        url=str(item["url"]),
                        timestamp=str(item["timestamp"]),
                        mime=str(item.get("mime", "")),
                        status=str(item.get("status", "")),
                        length=int(item["length"]),
                        offset=int(item["offset"]),
                        filename=str(item["filename"]),
                        digest=(
                            str(item["digest"])
                            if item.get("digest") is not None
                            else None
                        ),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise CdxError(
                    f"Некорректная CDX-запись в строке {line_number}: {item!r}"
                ) from exc

        return records


def response_to_dict(line: str) -> dict[str, Any]:
    """Парсит одну строку NDJSON-ответа CDX в словарь.

    Бросает ValueError, если строка не является корректным JSON-объектом.
    """

    import json

    payload = json.loads(line)
    if not isinstance(payload, dict):
        raise ValueError("ожидался JSON-объект")
    return payload
