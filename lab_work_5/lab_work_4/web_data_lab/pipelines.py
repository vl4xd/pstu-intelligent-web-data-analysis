
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

from lab_work_4.web_data_lab.utils.text_cleaner import clean_text
from lab_work_4.web_data_lab.utils.validators import validate_item


class CleaningPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        text_fields = ["title", "summary", "description"]

        for field in text_fields:
            if field in adapter and adapter[field]:
                adapter[field] = clean_text(adapter[field])

        spider.logger.debug("CleaningPipeline: item cleaned")
        return item


class DuplicationPipeline:
    def __init__(self):
        self.seen_urls = set()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        url = adapter.get("url")

        if not url:
            return item

        if url in self.seen_urls:
            spider.logger.info(
                f"DuplicationPipeline: duplicate skipped: {url}"
            )
            raise DropItem(f"Duplicate URL: {url}")

        self.seen_urls.add(url)
        return item


class ValidationPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        if not validate_item(adapter):
            spider.logger.warning(
                "ValidationPipeline: invalid item, skipped"
            )
            raise DropItem("Missing required fields: title or url")

        return item
