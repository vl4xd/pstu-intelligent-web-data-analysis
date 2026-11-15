from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import scrapy

from bs4 import BeautifulSoup
from scrapy.crawler import CrawlerProcess
from w3lib.url import canonicalize_url

from cacher import JsonPageCache


BASE_DIR = Path(__file__).resolve().parent
CACHE_PATH = BASE_DIR / "cache.json"


def normalize_url(url: str) -> str:
    """Нормализует URL и удаляет фрагмент (#...)."""
    return canonicalize_url(url, keep_fragments=False)


def get_host(url: str) -> str:
    """Получает имя хоста без www."""
    host = urlparse(url).hostname or ""
    host = host.lower()

    host = host.removeprefix("www.")

    return host

class GenericSpider(scrapy.Spider):

    name = "generic"

    def __init__(
        self,
        start_urls: list[str],
        max_depth: int = 0,
        max_pages: int = 25,
        use_cache: bool = True,
        cache=None,
        pages=None,
        errors=None,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.start_urls = list(start_urls)
        self.max_depth = int(max_depth)
        self.max_pages = int(max_pages)
        self.limit_logged = False
        self.use_cache = use_cache

        self.cache = cache
        self.pages = pages if pages is not None else []

        # Список уже обработанных URL.
        self.visited = set()

        self.errors = errors if errors is not None else []

    def initial_requests(self):
        """Формирует начальные запросы."""

        for url in self.start_urls:
            root_host = get_host(url)

            yield from self.schedule_url(
                url,
                depth=0,
                root_host=root_host
            )

    async def start(self):
        """Начало работы паука в современных версиях Scrapy."""

        for request in self.initial_requests():
            yield request

    def start_requests(self):
        """Совместимость со старыми версиями Scrapy."""

        yield from self.initial_requests()

    def schedule_url(
        self,
        url: str,
        depth: int,
        root_host: str
    ):
        """
        Определяет, нужно ли загружать страницу
        или её можно взять из кэша.
        """

        # Используем стек, чтобы не вызывать функции рекурсивно
        # при обработке страниц из кэша.
        stack = [(url, depth)]

        while stack:

            current_url, current_depth = stack.pop()

            current_url = normalize_url(current_url)

            # Проверяем глубину.
            if current_depth > self.max_depth:
                continue

            # Проверяем хост.
            if get_host(current_url) != root_host:
                continue

            # Не обрабатываем один URL повторно.
            if current_url in self.visited:
                continue

            # Проверяем ограничение количества URL.
            if len(self.visited) >= self.max_pages:

                if not self.limit_logged:
                    self.logger.warning(
                        "Достигнут лимит URL: %d",
                        self.max_pages
                    )
                    self.limit_logged = True

                break

            self.visited.add(current_url)

            # Ищем страницу в кэше.
            cached_page = (
                self.cache.get(current_url)
                if self.use_cache
                else None
            )

            if cached_page is not None and isinstance(
                cached_page.get("links"), list
            ):

                self.logger.info(
                    "CACHE HIT: %s",
                    current_url
                )

                # Используем сохранённые данные.
                page_url = cached_page.get("url", current_url)

                self.add_page(
                    page_url,
                    cached_page,
                    current_depth,
                    from_cache=True
                )

                # Продолжаем обход ссылок из кэша.
                if current_depth < self.max_depth:

                    for link in reversed(cached_page["links"]):
                        stack.append((
                            link,
                            current_depth + 1
                        ))

            else:

                self.logger.info(
                    "DOWNLOAD: %s",
                    current_url
                )

                # Страницы нет в кэше — загружаем.
                yield scrapy.Request(
                    url=current_url,
                    callback=self.parse,
                    errback=self.handle_error,
                    meta={
                        "crawl_depth": current_depth,
                        "root_host": root_host
                    }
                )

    def parse(self, response):

        content_type = response.headers.get(
            "Content-Type", b""
        ).decode("latin-1").lower()

        # Принимаем только HTML.
        if (
            "text/html" not in content_type
            and "application/xhtml+xml" not in content_type
        ):
            return

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Сначала извлекаем ссылки.
        links = []

        for element in soup.select("a[href]"):

            href = element.get("href", "").strip()

            if not href:
                continue

            absolute_url = normalize_url(
                response.urljoin(href)
            )

            parsed = urlparse(absolute_url)

            if parsed.scheme not in ("http", "https"):
                continue

            # Ограничиваем обход текущим хостом.
            root_host = response.meta["root_host"]

            if get_host(absolute_url) != root_host:
                continue

            if absolute_url not in links:
                links.append(absolute_url)

        # Удаляем ненужные элементы перед извлечением текста.
        for element in soup(
            ["script", "style", "noscript"]
        ):
            element.decompose()

        # Извлекаем текст.
        text_parts = []
        seen_text = set()

        for element in soup.select(
            "p, h1, h2, h3, h4, h5, h6, li"
        ):
            text = element.get_text(" ", strip=True)

            if text and text not in seen_text:
                text_parts.append(text)
                seen_text.add(text)

        page_text = "\n".join(text_parts)

        # Формируем данные страницы.
        page_data = {
            "url": response.url,
            "text": page_text,
            "links": links,
            "status": response.status,
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }

        # Сохраняем в кэш по исходному адресу запроса.
        request_url = normalize_url(response.request.url)

        self.cache.set(
            request_url,
            page_data
        )

        # Добавляем страницу в результаты текущего запуска.
        self.add_page(
            response.url,
            page_data,
            response.meta["crawl_depth"],
            from_cache=False
        )

        # Получаем текущую глубину и исходный хост.
        current_depth = response.meta["crawl_depth"]
        root_host = response.meta["root_host"]

        # Продолжаем обход, если не достигнута максимальная глубина.
        if current_depth < self.max_depth:
            for link in links:
                yield from self.schedule_url(
                    link,
                    current_depth + 1,
                    root_host
                )

    def add_page(
        self,
        url: str,
        data: dict,
        depth: int,
        from_cache: bool
    ):
        """Добавляет страницу в результаты."""

        self.pages.append({
            "url": url,
            "domain": get_host(url),
            "text": data.get("text", ""),
            "depth": depth,
            "from_cache": from_cache
        })

    def handle_error(self, failure):

        response = getattr(failure.value, "response", None)

        if response is not None:
            url = response.url
            status = response.status
            error_message = f"HTTP {status}"
        else:
            url = failure.request.url
            status = None
            error_message = failure.getErrorMessage()

        error_data = {
            "url": url,
            "status": status,
            "error": error_message
        }

        self.errors.append(error_data)

        self.logger.warning(
            "Не удалось загрузить %s: %s",
            url,
            error_message
        )

def crawl_urls(
    start_urls: list[str],
    max_depth: int = 0,
    max_pages: int = 25,
    use_cache: bool = True
) -> list[dict]:

    cache = JsonPageCache(CACHE_PATH)

    pages = []
    errors = []

    settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 1.0,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_TIMEOUT": 20,
        "RETRY_TIMES": 2,
        "LOG_LEVEL": "INFO",
    }

    process = CrawlerProcess(settings=settings)

    process.crawl(
        GenericSpider,
        start_urls=start_urls,
        max_depth=max_depth,
        max_pages=max_pages,
        use_cache=use_cache,
        cache=cache,
        pages=pages,
        errors=errors
    )

    try:
        process.start()
    finally:
        # Сохраняем кэш после завершения обхода.
        cache.save()

    return pages, errors