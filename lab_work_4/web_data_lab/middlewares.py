
from scrapy import signals


class WebDataLabSpiderMiddleware:
    """
    Spider middleware для логирования обработки ответов.
    """

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(
            middleware.spider_opened,
            signal=signals.spider_opened,
        )
        return middleware

    def spider_opened(self, spider):
        spider.logger.info(
            f"Spider started: {spider.name}"
        )

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(
        self, response, result, spider
    ):
        yield from result

    async def process_spider_output_async(
        self, response, result, spider
    ):
        async for item in result:
            yield item

    def process_spider_exception(
        self, response, exception, spider
    ):
        spider.logger.error(
            f"Spider exception on {response.url}: {exception}"
        )
        return None

    def process_start_requests(self, start_requests, spider):
        yield from start_requests

    def process_spider_closed(self, spider):
        spider.logger.info(
            f"Spider closed: {spider.name}"
        )


class WebDataLabDownloaderMiddleware:
    """
    Downloader middleware для логирования HTTP-ответов.
    """

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        return None

    def process_response(self, request, response, spider):
        if response.status in (429, 503):
            spider.logger.warning(
                f"HTTP {response.status}: {response.url}"
            )

        return response

    def process_exception(self, request, exception, spider):
        spider.logger.error(
            f"Request exception: {request.url}: {exception}"
        )
        return None
