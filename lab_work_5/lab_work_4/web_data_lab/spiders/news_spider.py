
from datetime import datetime, timezone

import scrapy

from web_data_lab.items import NewsItem
from web_data_lab.loaders.item_loaders import NewsItemLoader


class NewsSpider(scrapy.Spider):
    """
    Паук для сбора публикаций с Habr.

    Источник: https://habr.com/ru/articles/
    Тип сайта: SSR.
    """

    name = "news"
    allowed_domains = ["habr.com"]

    start_urls = [
        "https://habr.com/ru/articles/"
    ]

    def __init__(
        self,
        keywords=None,
        limit=100,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        # Ключевые слова для фильтрации публикаций
        self.keywords = [
            word.strip().casefold()
            for word in (keywords or "").split(",")
            if word.strip()
        ]

        # Минимальное количество собираемых записей
        self.limit = int(limit)

        self.collected_count = 0
        self.seen_urls = set()

    def parse(self, response):
        """
        Обрабатывает страницу списка публикаций.
        """

        self.logger.info(
            f"Processing page: {response.url}"
        )

        articles = response.css(
            "article.tm-articles-list__item"
        )

        for article in articles:

            if self.collected_count >= self.limit:
                break

            loader = NewsItemLoader(
                item=NewsItem(),
                selector=article
            )

            loader.add_css(
                "title",
                "h2.tm-title a span::text"
            )

            loader.add_css(
                "url",
                "h2.tm-title a::attr(href)"
            )

            loader.add_value(
                "source",
                "Habr"
            )

            loader.add_css(
                "author",
                "a.tm-user-info__username::text"
            )

            loader.add_css(
                "published_at",
                "time::attr(datetime)"
            )

            loader.add_css(
                "summary",
                "div.article-formatted-body p::text"
            )

            loader.add_value(
                "collected_at",
                datetime.now(timezone.utc).isoformat()
            )

            item = loader.load_item()

            title = item.get("title", "")

            # Фильтрация по ключевым словам
            if self.keywords:
                text = title.casefold()

                if not any(
                    keyword in text
                    for keyword in self.keywords
                ):
                    continue

            url = item.get("url")

            if not url:
                continue

            item["url"] = response.urljoin(url)

            # Удаление повторных URL
            if item["url"] in self.seen_urls:
                continue

            self.seen_urls.add(item["url"])

            self.collected_count += 1

            self.logger.info(
                f"Collected {self.collected_count}/"
                f"{self.limit}: {title}"
            )

            yield item

        # Переход на следующую страницу
        if self.collected_count < self.limit:

            next_page = response.css(
                "a#pagination-next-page::attr(href)"
            ).get()

            if next_page:
                yield response.follow(
                    next_page,
                    callback=self.parse
                )
            else:
                self.logger.info(
                    "No more pages available"
                )
