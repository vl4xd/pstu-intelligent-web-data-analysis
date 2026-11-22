
from scrapy.http import HtmlResponse

from lab_work_5.lab_work_4.web_data_lab.spiders.news_spider import NewsSpider
from lab_work_5.lab_work_4.web_data_lab.spiders.ecommerce_spider import EcommerceSpider


def test_news_spider_parses_article():
    spider = NewsSpider(limit=1)

    html = """
    <html>
      <body>
        <article class="tm-articles-list__item">
          <h2 class="tm-title">
            <a href="/ru/articles/123/">
              <span>Test Python Article</span>
            </a>
          </h2>
          <a class="tm-user-info__username">Test Author</a>
          <time datetime="2026-11-21T10:00:00+00:00"></time>
          <div class="article-formatted-body">
            <p>Test article summary</p>
          </div>
        </article>
      </body>
    </html>
    """

    response = HtmlResponse(
        url="https://habr.com/ru/articles/",
        body=html,
        encoding="utf-8",
    )

    items = list(spider.parse(response))

    assert len(items) == 1
    assert items[0]["title"] == "Test Python Article"
    assert items[0]["url"] == "https://habr.com/ru/articles/123/"
    assert items[0]["source"] == "Habr"


def test_ecommerce_spider_parses_product():
    spider = EcommerceSpider(limit=1)

    html = """
    <html>
      <body>
        <div class="dynamic_catalog_card">
          <div class="dynamic_catalog_card_name">
            Test Product
          </div>
          <div class="dynamic_catalog_card_price">$19.99</div>
          <img class="dynamic_catalog_card_img"
               src="/assets/test-product.jpg">
        </div>
      </body>
    </html>
    """

    response = HtmlResponse(
        url=spider.catalog_url,
        body=html,
        encoding="utf-8",
    )

    items = list(spider.parse_catalog(response))

    assert len(items) == 1
    assert items[0]["title"] == "Test Product"
    assert items[0]["price"] == "$19.99"
    assert items[0]["currency"] == "USD"
    assert items[0]["source"] == "SauceDemo"
    assert items[0]["image"] == (
        "https://www.saucedemo.com/assets/test-product.jpg"
    )
    assert items[0]["description"] == ""
