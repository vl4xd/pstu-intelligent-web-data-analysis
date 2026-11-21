
from datetime import datetime, timezone

import scrapy
from scrapy_playwright.page import PageMethod

from web_data_lab.items import ProductItem
from web_data_lab.loaders.item_loaders import ProductItemLoader


class EcommerceSpider(scrapy.Spider):
    """
    Паук для сбора товаров с SauceDemo.

    Источник: SauceDemo
    Тип сайта: SPA (React)
    Технология: Playwright, Lazy Loading
    """

    name = "ecommerce"
    allowed_domains = ["saucedemo.com"]

    login_url = "https://www.saucedemo.com/"
    catalog_url = (
        "https://www.saucedemo.com/"
        "dynamic-catalog-lazy-load.html"
    )

    def __init__(
        self,
        keywords=None,
        limit=100,
        username="standard_user",
        password="secret_sauce",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.keywords = [
            word.strip().casefold()
            for word in (keywords or "").split(",")
            if word.strip()
        ]

        self.limit = int(limit)
        self.username = username
        self.password = password

        self.collected_count = 0
        self.seen_urls = set()

    async def start(self):
        yield scrapy.Request(
            url=self.login_url,
            callback=self.parse_catalog,
            meta={
                "playwright": True,
                "playwright_page_methods": [
                    PageMethod(
                        "fill",
                        '[data-test="username"]',
                        self.username,
                    ),
                    PageMethod(
                        "fill",
                        '[data-test="password"]',
                        self.password,
                    ),
                    PageMethod(
                        "click",
                        '[data-test="login-button"]',
                    ),
                    PageMethod(
                        "wait_for_url",
                        "**/inventory.html",
                    ),
                    PageMethod(
                        "goto",
                        self.catalog_url,
                        wait_until="domcontentloaded",
                    ),
                    PageMethod(
                        "wait_for_selector",
                        ".dynamic_catalog_card_name",
                    ),
                    PageMethod(
                        "evaluate",
                        f"""
                        async () => {{
                            for (let step = 0; step < 25; step++) {{
                                window.scrollTo(
                                    0,
                                    document.body.scrollHeight
                                );

                                await new Promise(resolve =>
                                    setTimeout(resolve, 1500)
                                );

                                const loaded = document.querySelectorAll(
                                    ".dynamic_catalog_card_name"
                                ).length;

                                if (loaded >= {self.limit}) {{
                                    break;
                                }}
                            }}
                        }}
                        """,
                    ),
                ],
            },
            errback=self.request_failed,
        )

    def parse_catalog(self, response):
        self.logger.info(
            f"Processing catalog: {response.url}"
        )

        cards = response.css(
            ".dynamic_catalog_card"
        )

        self.logger.info(
            f"Loaded product cards: {len(cards)}"
        )

        for index, card in enumerate(cards):
            if self.collected_count >= self.limit:
                break

            title = card.css(
                ".dynamic_catalog_card_name::text"
            ).get()

            price = card.css(
                ".dynamic_catalog_card_price::text"
            ).get()

            image = card.css(
                ".dynamic_catalog_card_img::attr(src)"
            ).get()

            if not title:
                continue

            title = title.strip()

            if self.keywords:
                title_lower = title.casefold()

                if not any(
                    keyword in title_lower
                    for keyword in self.keywords
                ):
                    continue

            product_url = (
                f"{self.catalog_url}#product-{index}"
            )

            if product_url in self.seen_urls:
                continue

            loader = ProductItemLoader(
                item=ProductItem(),
                selector=card,
            )

            loader.add_value("title", title)
            loader.add_value("url", product_url)
            loader.add_value("source", "SauceDemo")
            loader.add_value("category", "Products")
            loader.add_value("price", price)
            loader.add_value("currency", "USD")
            loader.add_value("availability", "available")
            loader.add_value("description", "")
            loader.add_value("image", response.urljoin(image) if image else "")
            loader.add_value("collected_at", datetime.now(timezone.utc).isoformat())
            item = loader.load_item()

            self.seen_urls.add(product_url)
            self.collected_count += 1

            self.logger.info(
                f"Collected "
                f"{self.collected_count}/{self.limit}: "
                f"{title}"
            )

            yield item

        self.logger.info(
            f"Collection finished. "
            f"Total products: {self.collected_count}"
        )

    def request_failed(self, failure):
        self.logger.error(
            f"Playwright request failed: {failure}"
        )
