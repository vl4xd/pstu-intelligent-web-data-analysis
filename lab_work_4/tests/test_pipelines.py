import logging

import pytest
from scrapy.exceptions import DropItem

from web_data_lab.pipelines import (
    CleaningPipeline,
    DuplicationPipeline,
    ValidationPipeline,
)


class FakeSpider:
    logger = logging.getLogger("test_spider")


def test_cleaning_pipeline():
    pipeline = CleaningPipeline()
    item = {
        "title": "  HELLO   WORLD  ",
        "summary": " SOME TEXT ",
        "description": " DESCRIPTION ",
        "url": "https://example.com",
    }

    result = pipeline.process_item(item, FakeSpider())

    assert result["title"] == "hello world"
    assert result["summary"] == "some text"
    assert result["description"] == "description"


def test_duplication_pipeline_accepts_unique_item():
    pipeline = DuplicationPipeline()
    item = {
        "title": "Test",
        "url": "https://example.com/1",
    }

    result = pipeline.process_item(item, FakeSpider())

    assert result == item


def test_duplication_pipeline_rejects_duplicate():
    pipeline = DuplicationPipeline()
    item = {
        "title": "Test",
        "url": "https://example.com/1",
    }

    pipeline.process_item(item, FakeSpider())

    with pytest.raises(DropItem):
        pipeline.process_item(item, FakeSpider())


def test_validation_pipeline_accepts_valid_item():
    pipeline = ValidationPipeline()
    item = {
        "title": "Test",
        "url": "https://example.com",
    }

    result = pipeline.process_item(item, FakeSpider())

    assert result == item


def test_validation_pipeline_rejects_item_without_title():
    pipeline = ValidationPipeline()
    item = {
        "title": "",
        "url": "https://example.com",
    }

    with pytest.raises(DropItem):
        pipeline.process_item(item, FakeSpider())


def test_duplication_pipeline_accepts_item_without_url():
    pipeline = DuplicationPipeline()
    item = {
        "title": "Test without URL",
    }

    result = pipeline.process_item(item, FakeSpider())

    assert result == item