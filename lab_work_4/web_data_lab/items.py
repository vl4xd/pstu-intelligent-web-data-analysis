
import scrapy


class NewsItem(scrapy.Item):
    """
    Структура данных для новостных публикаций.

    Используется NewsSpider для сбора информации
    со статических новостных сайтов (SSR).
    """

    # Основная информация
    title = scrapy.Field()
    url = scrapy.Field()

    # Источник публикации
    source = scrapy.Field()

    # Дополнительная информация
    author = scrapy.Field()
    published_at = scrapy.Field()
    summary = scrapy.Field()

    # Служебная информация
    collected_at = scrapy.Field()


class ProductItem(scrapy.Item):
    """
    Структура данных для товаров интернет-магазинов.

    Используется EcommerceSpider для сбора информации
    с динамических сайтов (SPA) через Playwright.
    """

    # Основная информация
    title = scrapy.Field()
    url = scrapy.Field()

    # Информация о магазине
    source = scrapy.Field()
    category = scrapy.Field()

    # Характеристики товара
    price = scrapy.Field()
    currency = scrapy.Field()
    rating = scrapy.Field()
    availability = scrapy.Field()
    description = scrapy.Field()
    image = scrapy.Field()
    
    # Служебная информация
    collected_at = scrapy.Field()
