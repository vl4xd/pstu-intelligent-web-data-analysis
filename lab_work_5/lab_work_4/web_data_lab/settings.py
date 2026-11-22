
BOT_NAME = "web_data_lab"

SPIDER_MODULES = ["web_data_lab.spiders"]
NEWSPIDER_MODULE = "web_data_lab.spiders"

# Соблюдение правил сайтов
ROBOTSTXT_OBEY = True

# Задержки и параллельность запросов
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 1.0
RANDOMIZE_DOWNLOAD_DELAY = True

# Повторные запросы при временных HTTP-ошибках
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [429, 500, 502, 503, 504]

# Тайм-аут загрузки
DOWNLOAD_TIMEOUT = 30

# Настройки Playwright для SPA
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

TWISTED_REACTOR = (
    "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
)

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "timeout": 30_000,
}

PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30_000
PLAYWRIGHT_MAX_CONTEXTS = 4

# Кодировка
FEED_EXPORT_ENCODING = "utf-8"

# Логирование
LOG_LEVEL = "INFO"
LOG_FILE = "logs/scrapy.log"

# Pipelines
ITEM_PIPELINES = {
    "web_data_lab.pipelines.CleaningPipeline": 100,
    "web_data_lab.pipelines.DuplicationPipeline": 200,
    "web_data_lab.pipelines.ValidationPipeline": 300,
}

# User-Agent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

SPIDER_MIDDLEWARES = {
    "web_data_lab.middlewares.WebDataLabSpiderMiddleware": 543,
}

DOWNLOADER_MIDDLEWARES = {
    "web_data_lab.middlewares.WebDataLabDownloaderMiddleware": 543,
}

