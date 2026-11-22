from lab_work_5.lab_work_4.web_data_lab.items import NewsItem, ProductItem


def test_news_item_fields():
    item = NewsItem()

    expected_fields = {
        "title",
        "url",
        "source",
        "author",
        "published_at",
        "summary",
        "collected_at",
    }

    assert set(item.fields.keys()) == expected_fields


def test_product_item_fields():
    item = ProductItem()

    expected_fields = {
        "title",
        "url",
        "source",
        "category",
        "price",
        "currency",
        "rating",
        "availability",
        "description",
        "image",
        "collected_at",
    }

    assert set(item.fields.keys()) == expected_fields