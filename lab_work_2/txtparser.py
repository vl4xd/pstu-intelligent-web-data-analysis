from pathlib import Path
from urllib.parse import urlparse


def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)

        # Проверяем протокол
        if parsed.scheme not in ("http", "https"):
            return False

        # Проверяем наличие доменного имени
        if not parsed.hostname:
            return False

        # Проверяем корректность порта
        if parsed.port is not None:
            return 1 <= parsed.port <= 65535
        return True
    except ValueError:
        return False

def parse_urls(data_path: str) -> tuple[list[str], list[tuple[int, str]]]:
    correct_urls = []
    incorrect_urls = []
    with open(data_path, 'r', encoding='utf-8') as f:
        for line_number, line in enumerate(f, start=1):
            curr_url = line.strip()
            # Пусткая строка
            if not curr_url:
                incorrect_urls.append((line_number, curr_url))
                continue

            if is_valid_url(curr_url):
                if curr_url not in correct_urls:
                    correct_urls.append(curr_url)
                else:
                    incorrect_urls.append((line_number, curr_url, 'Повторное значение URL'))
            else:
                incorrect_urls.append((line_number, curr_url, 'Некорректный URL'))

    return correct_urls, incorrect_urls
