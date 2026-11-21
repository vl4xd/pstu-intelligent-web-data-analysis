
from web_data_lab.utils.text_cleaner import clean_text
from web_data_lab.utils.validators import validate_item


def test_clean_text():
    assert clean_text("  HELLO   WORLD  ") == "hello world"


def test_clean_text_encoding():
    assert clean_text("cafÃ©") == "café"


def test_validate_item_success():
    item = {
        "title": "Ноутбук",
        "url": "https://example.com",
    }

    assert validate_item(item) is True


def test_validate_item_missing_title():
    item = {
        "title": "",
        "url": "https://example.com",
    }

    assert validate_item(item) is False


def test_validate_item_missing_url():
    item = {
        "title": "Ноутбук",
        "url": "",
    }

    assert validate_item(item) is False
