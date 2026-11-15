import inspect

from collections import defaultdict, namedtuple
from collections.abc import Mapping
from urllib.parse import urlparse


# Совместимость pymorphy2 с Python 3.11+
if not hasattr(inspect, "getargspec"):

    ArgSpec = namedtuple(
        "ArgSpec",
        ["args", "varargs", "keywords", "defaults"]
    )

    def getargspec(func):
        spec = inspect.getfullargspec(func)

        return ArgSpec(
            spec.args,
            spec.varargs,
            spec.varkw,
            spec.defaults
        )

    inspect.getargspec = getargspec


# Импортируем после настройки совместимости.
from rutermextract import TermExtractor


def get_domain(page: dict) -> str | None:
    """
    Получает домен страницы.

    Если domain отсутствует, пытается извлечь
    его из URL.
    """

    domain = page.get("domain")

    if not domain:
        url = page.get("url")

        if not url:
            return None

        domain = urlparse(url).hostname

    if not domain:
        return None

    return str(domain).strip().lower().removeprefix("www.")


def extract_site_terms(
    pages: list[dict],
    limit_per_site: int = 200,
    nested: bool = False
) -> dict[str, set[str]]:
    """
    Извлекает ключевые термины и группирует их по доменам.

    Args:
        pages: Результаты работы Scrapy.
        limit_per_site: Максимальное количество терминов
                        для одного сайта.
        nested: Извлекать ли вложенные термины.

    Returns:
        Словарь вида {domain: set(terms)}.
    """

    if limit_per_site < 1:
        raise ValueError(
            "limit_per_site должен быть >= 1"
        )

    # Группируем тексты страниц по доменам.
    site_texts = defaultdict(list)

    # Защита от повторной обработки одной страницы.
    seen_urls = set()

    for page in pages:

        if not isinstance(page, Mapping):
            continue

        text = page.get("text")

        if not isinstance(text, str) or not text.strip():
            continue

        domain = get_domain(page)

        if not domain:
            continue

        url = page.get("url")

        if url:
            url = str(url).strip()

            if url in seen_urls:
                continue

            seen_urls.add(url)

        site_texts[domain].append(text.strip())

    # Создаём один экземпляр извлекателя.
    extractor = TermExtractor()

    site_terms = {}

    # Обрабатываем каждый сайт отдельно.
    for domain, texts in site_texts.items():

        # Объединяем тексты страниц одного сайта.
        full_text = "\n\n".join(texts)

        # Извлекаем нормализованные термины.
        extracted = extractor(
            full_text,
            limit=limit_per_site,
            nested=nested,
            strings=True
        )

        # Преобразуем результаты в множество.
        terms = {
            term.strip().casefold()
            for term in extracted
            if isinstance(term, str) and term.strip()
        }

        if terms:
            site_terms[domain] = terms

        print(
            f"{domain}: "
            f"страниц — {len(texts)}, "
            f"терминов — {len(terms)}"
        )

    return site_terms
