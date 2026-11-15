import argparse

from argparser import build_parser
from graph import build_graph
from spider import crawl_urls
from term_extractor import extract_site_terms
from txtparser import parse_urls


def run(args: argparse.Namespace) -> int:
    correct_urls, incorrect_urls = parse_urls(args.dataurls)

    if not correct_urls:
        print("Нет URL для обработки.")
        return 1
    
    pages, errors = crawl_urls(
        start_urls=correct_urls,
        max_depth=args.deep,
        max_pages=args.max_pages,
        use_cache=args.use_cache
    )

    print(f"\nСобрано страниц: {len(pages)}")

    cache_hits = sum(
        page["from_cache"] for page in pages
    )

    print(f"Взято из кэша: {cache_hits}")
    print(f"Загружено заново: {len(pages) - cache_hits}")

    print(f"\nОшибок загрузки: {len(errors)}")

    for error in errors:
        print(
            f"[{error['status'] or 'NETWORK ERROR'}] "
            f"{error['url']}: {error['error']}"
        )

    site_terms = extract_site_terms(
        pages,
        limit_per_site=200
    )

    if not site_terms:
        print("Не удалось извлечь термины.")
        return 1

    graph_path = build_graph(
        site_terms=site_terms,
        min_common_terms=args.min_common
    )

    print(f"Граф сохранён: {graph_path}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    run(args)

if __name__ == '__main__':
    raise SystemExit(main())

    