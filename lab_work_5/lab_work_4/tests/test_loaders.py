from lab_work_5.lab_work_4.web_data_lab.items import NewsItem, ProductItem
from lab_work_5.lab_work_4.web_data_lab.loaders.item_loaders import (
    NewsItemLoader,
    ProductItemLoader,
)


def test_news_item_loader():
    loader = NewsItemLoader(item=NewsItem())
    loader.add_value("title", "  Test News  ")
    loader.add_value("url", "https://example.com/news")
    loader.add_value("source", "Habr")
    loader.add_value("summary", ["First paragraph", "Second paragraph"])

    item = loader.load_item()

    assert item["title"] == "Test News"
    assert item["url"] == "https://example.com/news"
    assert item["source"] == "Habr"
    assert item["summary"] == "First paragraph Second paragraph"


def test_product_item_loader():
    loader = ProductItemLoader(item=ProductItem())
    loader.add_value("title", "  Test Product  ")
    loader.add_value("url", "https://example.com/product")
    loader.add_value("price", "$19.99")
    loader.add_value("currency", "USD")
    loader.add_value("image", "https://example.com/image.jpg")

    item = loader.load_item()
    
    assert item["title"] == "Test Product"
    assert item["url"] == "https://example.com/product"
    assert item["price"] == "$19.99"
    assert item["currency"] == "USD"
    assert item["image"] == "https://example.com/image.jpg"