
import argparse
import os
from pathlib import Path

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from web_data_lab.spiders.news_spider import NewsSpider
from web_data_lab.spiders.ecommerce_spider import EcommerceSpider


SPIDERS = {
    "news": NewsSpider,
    "ecommerce": EcommerceSpider,
}


def main():
    parser = argparse.ArgumentParser(
        description="Web Data Lab - запуск пауков Scrapy"
    )

    parser.add_argument(
        "--spider",
        choices=SPIDERS.keys(),
        required=True,
        help="Паук для запуска: news или ecommerce",
    )

    parser.add_argument(
        "--keywords",
        default="",
        help="Ключевые слова через запятую",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Путь к выходному файлу JSON или CSV",
    )

    args = parser.parse_args()

    spider_class = SPIDERS[args.spider]

    output_path = args.output or f"data/raw/{args.spider}.json"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    settings = get_project_settings()
    settings.set("FEEDS", {
        output_path: {
            "format": Path(output_path).suffix.lstrip("."),
            "encoding": "utf-8",
            "overwrite": True,
        }
    })

    process = CrawlerProcess(settings)

    process.crawl(
        spider_class,
        keywords=args.keywords,
        limit=100,
    )

    process.start()


if __name__ == "__main__":
    main()
