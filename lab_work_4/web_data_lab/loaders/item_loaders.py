
from itemloaders import ItemLoader
from itemloaders.processors import MapCompose, TakeFirst, Join

from web_data_lab.items import NewsItem, ProductItem


def strip_text(value):
    """Удаляет пробелы в начале и конце строки."""
    if isinstance(value, str):
        return value.strip()
    return value


class NewsItemLoader(ItemLoader):
    """
    Loader для извлечения и обработки новостей.
    """

    default_item_class = NewsItem
    default_input_processor = MapCompose(strip_text)
    default_output_processor = TakeFirst()

    title_in = MapCompose(strip_text)
    url_in = MapCompose(strip_text)
    source_in = MapCompose(strip_text)
    author_in = MapCompose(strip_text)
    published_at_in = MapCompose(strip_text)

    summary_in = MapCompose(strip_text)
    summary_out = Join(" ")


class ProductItemLoader(ItemLoader):
    """
    Loader для извлечения и обработки товаров.
    """

    default_item_class = ProductItem
    default_input_processor = MapCompose(strip_text)
    default_output_processor = TakeFirst()

    title_in = MapCompose(strip_text)
    url_in = MapCompose(strip_text)
    source_in = MapCompose(strip_text)
    category_in = MapCompose(strip_text)

    price_in = MapCompose(strip_text)
    currency_in = MapCompose(strip_text)
    rating_in = MapCompose(strip_text)
    availability_in = MapCompose(strip_text)

    description_in = MapCompose(strip_text)
    description_out = Join(" ")
    image_in = MapCompose(strip_text)
