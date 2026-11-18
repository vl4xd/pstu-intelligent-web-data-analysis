import os
import time
import requests

from collections import deque
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

from models.article import Article
from collectors.exceptions import (
    WikimediaError,
    NetworkError,
    ServerUnavailableError,
    RateLimitError,
    APIError,
    InvalidResponseError
)


class WikipediaCollector:

    def __init__(self, language="ru", delay=1.2):

        self.language = language
        self.delay = delay

        self.api_url = (
            f"https://{language}.wikipedia.org/w/api.php"
        )

        # Контактные данные желательно указать через переменную окружения
        contact = os.getenv(
            "WIKIMEDIA_CONTACT",
            "your-email@example.com"
        )

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                f"WikimediaLab3/1.0 ({contact})"
            ),
            "Accept-Encoding": "gzip"
        })

        self.last_request_time = 0

    def _get_retry_after(self, response, default):
        """Получение времени ожидания из Retry-After."""

        value = response.headers.get("Retry-After")

        if not value:
            return default

        try:
            return max(0, float(value))
        except ValueError:
            try:
                retry_date = parsedate_to_datetime(value)

                if retry_date.tzinfo is None:
                    retry_date = retry_date.replace(
                        tzinfo=timezone.utc
                    )

                wait = (
                    retry_date -
                    datetime.now(timezone.utc)
                ).total_seconds()

                return max(0, wait)

            except (TypeError, ValueError):
                return default

    def _wait_before_request(self):
        """Ограничение частоты запросов."""

        elapsed = time.monotonic() - self.last_request_time

        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

        self.last_request_time = time.monotonic()

    def _request(self, params):
        """Выполнение запроса с обработкой сетевых и API-ошибок."""

        params = {
            **params,
            "format": "json",
            "formatversion": 2,
            "maxlag": 5
        }

        max_retries = 5

        for attempt in range(max_retries):

            self._wait_before_request()

            try:
                response = self.session.get(
                    self.api_url,
                    params=params,
                    timeout=(10, 30)
                )

            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    raise NetworkError(
                        "Превышено время ожидания ответа Wikimedia."
                    )

                wait = min(2 ** (attempt + 1), 30)

                print(
                    f"[ПРЕДУПРЕЖДЕНИЕ] Таймаут соединения. "
                    f"Повтор через {wait} сек."
                )

                time.sleep(wait)
                continue

            except requests.exceptions.ConnectionError:
                if attempt == max_retries - 1:
                    raise NetworkError(
                        "Не удалось подключиться к Wikimedia. "
                        "Проверьте интернет-соединение."
                    )

                wait = min(2 ** (attempt + 1), 30)

                print(
                    f"[ПРЕДУПРЕЖДЕНИЕ] Сервер недоступен. "
                    f"Повтор через {wait} сек."
                )

                time.sleep(wait)
                continue

            except requests.exceptions.RequestException as error:
                raise NetworkError(
                    f"Ошибка HTTP-запроса: {error}"
                ) from error

            status = response.status_code

            # Ограничение запросов
            if status == 429:
                wait = self._get_retry_after(
                    response,
                    min(5 * (2 ** attempt), 60)
                )

                if attempt == max_retries - 1:
                    raise RateLimitError(
                        "Превышен лимит запросов Wikimedia. "
                        "Попробуйте позже."
                    )

                print(
                    f"[ПРЕДУПРЕЖДЕНИЕ] HTTP 429. "
                    f"Ожидание {wait:.1f} сек."
                )

                time.sleep(wait)
                continue

            # Временные ошибки сервера
            if status in (500, 502, 503, 504):

                wait = self._get_retry_after(
                    response,
                    min(2 ** (attempt + 1), 30)
                )

                if attempt == max_retries - 1:
                    raise ServerUnavailableError(
                        f"Wikimedia временно недоступна "
                        f"(HTTP {status}). Попробуйте позже."
                    )

                print(
                    f"[ПРЕДУПРЕЖДЕНИЕ] Ошибка сервера "
                    f"HTTP {status}. Повтор через {wait:.1f} сек."
                )

                time.sleep(wait)
                continue

            # Остальные HTTP-ошибки
            try:
                response.raise_for_status()

            except requests.exceptions.HTTPError as error:
                raise APIError(
                    f"HTTP-ошибка {status}. "
                    "Проверьте запрос и доступность API."
                ) from error

            # Проверка корректности JSON
            try:
                data = response.json()

            except ValueError as error:
                if attempt == max_retries - 1:
                    raise InvalidResponseError(
                        "Wikimedia вернула некорректный JSON."
                    ) from error

                wait = min(2 ** (attempt + 1), 30)

                print(
                    f"[ПРЕДУПРЕЖДЕНИЕ] "
                    f"Некорректный ответ сервера. "
                    f"Повтор через {wait} сек."
                )

                time.sleep(wait)
                continue

            # Проверка ошибок самого MediaWiki API
            if "error" in data:

                api_error = data["error"]
                error_code = api_error.get("code", "unknown")
                error_info = api_error.get("info", "")

                if error_code in ("maxlag", "ratelimited"):

                    wait = min(5 * (2 ** attempt), 60)

                    if attempt == max_retries - 1:
                        raise RateLimitError(
                            f"Ограничение Wikimedia API: "
                            f"{error_code}. {error_info}"
                        )

                    print(
                        f"[ПРЕДУПРЕЖДЕНИЕ] "
                        f"API {error_code}. "
                        f"Повтор через {wait} сек."
                    )

                    time.sleep(wait)
                    continue

                raise APIError(
                    f"Ошибка Wikimedia API: "
                    f"{error_code}. {error_info}"
                )

            return data

        raise WikimediaError(
            "Не удалось выполнить запрос к Wikimedia."
        )

    def search_article(self, query):
        """Поиск начальной статьи."""

        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srnamespace": 0,
            "srlimit": 1
        }

        data = self._request(params)

        results = data["query"]["search"]

        if not results:
            return None

        return results[0]["title"]

    def get_article(self, title):
        """Получение статьи и её ссылок."""

        params = {
            "action": "query",
            "prop": "extracts|links",
            "titles": title,
            "explaintext": 1,
            "exsectionformat": "plain",
            "plnamespace": 0,
            "pllimit": 50,
            "redirects": 1
        }

        data = self._request(params)

        pages = data["query"]["pages"]

        if not pages:
            return None

        page = pages[0]

        if "missing" in page:
            return None

        links = [
            link["title"]
            for link in page.get("links", [])
        ]

        article = Article(
            title=page["title"],
            language=self.language,
            url=(
                f"https://{self.language}.wikipedia.org/wiki/"
                + requests.utils.quote(
                    page["title"].replace(" ", "_")
                )
            ),
            text=page.get("extract", ""),
            links=links
        )

        return article

    def collect_articles(self, query, max_articles=30):
        """Сбор статей с помощью BFS."""

        root_title = self.search_article(query)

        if root_title is None:
            print("Статья по запросу не найдена.")
            return []

        queue = deque([root_title])

        visited = set()
        articles = []

        while queue and len(articles) < max_articles:

            current_title = queue.popleft()

            normalized_title = current_title.casefold()

            if normalized_title in visited:
                continue

            visited.add(normalized_title)

            try:
                article = self.get_article(current_title)

                if article is None:
                    print(
                        f"[ПРОПУСК] Статья не найдена: {current_title}"
                    )
                    continue

                articles.append(article)

                print(
                    f"[{len(articles)}/{max_articles}] "
                    f"Получена статья: {article.title}"
                )

                for link in article.links:
                    if link.casefold() not in visited:
                        queue.append(link)

            except RateLimitError as error:
                print(f"\n[ОШИБКА] {error}")
                break

            except NetworkError as error:
                print(f"\n[ОШИБКА СЕТИ] {error}")
                break

            except ServerUnavailableError as error:
                print(f"\n[ОШИБКА СЕРВЕРА] {error}")
                break

            except InvalidResponseError as error:
                print(f"[ОШИБКА ОТВЕТА] {current_title}: {error}")

            except APIError as error:
                print(f"[ОШИБКА API] {current_title}: {error}")

            except requests.RequestException as error:
                print(f"[ОШИБКА HTTP] {current_title}: {error}")

            except (KeyError, ValueError, TypeError) as error:
                print(f"[ОШИБКА ДАННЫХ] {current_title}: {error}")

        return articles