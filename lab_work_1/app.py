from __future__ import annotations

import argparse
import sys
from typing import Sequence

from tabulate import tabulate

from tqdm.auto import tqdm

from cdx import CdxClient, CdxError, CdxRecord
from warc import WARCClient, WARCError, find_matching_page


def build_parser() -> argparse.ArgumentParser:
    """Создаёт и настраивает парсер аргументов командной строки.

    Возвращает готовый ArgumentParser со всеми опциями CLI:
    ключевыми словами, доменами, лимитами, таймаутами и т.д.
    """

    parser = argparse.ArgumentParser(
        prog="common-crawl-search",
        description=(
            "Поиск ключевых слов в HTML-страницах последнего "
            "или указанного Common Crawl индекса."
        ),
    )
    parser.add_argument(
        "keywords",
        nargs="+",
        help=(
            "Одно или несколько ключевых слов/фраз. "
            "Все указанные слова должны встретиться на странице."
        ),
    )
    parser.add_argument(
        "-d",
        "--domains",
        nargs="+",
        required=True,
        help=(
            "Один или несколько доменов для поиска, например example.com или example1.com example2.com. "
            "Поиск включает поддомены."
        ),
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=positive_int,
        default=10,
        metavar="N",
        help="Максимальное число найденных страниц (по умолчанию: 10).",
    )
    parser.add_argument(
        "-st",
        "--show-text",
        action="store_true",
        dest="show_text",
        help="Показать фрагмент текста вокруг первого совпадения.",
    )
    parser.add_argument(
        "--crawl",
        default=None,
        help=(
            "Идентификатор Common Crawl индекса, например "
            "CC-MAIN-2026-34. По умолчанию используется последний индекс."
        ),
    )
    parser.add_argument(
        "--candidate-limit",
        type=positive_int,
        default=500,
        metavar="N",
        help=(
            "Максимальное число CDX-записей, которые будут проверены "
            "по содержимому WARC, для каждого домена  (по умолчанию: 500)."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=positive_float,
        default=60.0,
        metavar="SECONDS",
        help="HTTP timeout (по умолчанию: 60 секунд).",
    )
    parser.add_argument(
        "--delay",
        type=non_negative_float,
        default=2.0,
        metavar="SECONDS",
        help=(
            "Пауза между запросами к CDX/WARC (по умолчанию: 2 секунды). "
        ),
    )
    parser.add_argument(
        "--snippet-chars",
        type=positive_int,
        default=220,
        metavar="N",
        help=(
            "Максимальный размер текстового фрагмента "
            "(по умолчанию: 220 символов)."
        ),
    )
    return parser


def positive_int(value: str) -> int:
    """Преобразует строку в целое число, требуя значение > 0.

    Используется как type= в argparse для аргументов-лимитов.
    При некорректном значении бросает argparse.ArgumentTypeError.
    """

    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("значение должно быть > 0")
    return number


def positive_float(value: str) -> float:
    """Преобразует строку в число с плавающей точкой, требуя значение > 0.

    Применяется для аргументов вроде --timeout.
    """

    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("значение должно быть > 0")
    return number


def non_negative_float(value: str) -> float:
    """Преобразует строку в число с плавающей точкой, требуя значение >= 0.

    Применяется для аргумента --delay, где нулевая пауза допустима.
    """

    number = float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("значение должно быть >= 0")
    return number


def run(args: argparse.Namespace) -> int:
    """Основная логика программы: поиск ключевых слов в Common Crawl.

    Порядок работы:
      1. Определяет crawl id (из --crawl или последний доступный).
      2. Запрашивает CDX-кандидатов по каждому домену.
      3. Скачивает WARC-записи и парсит HTML.
      4. Ищет страницы, где встречаются все ключевые слова.
      5. Печатает таблицу результатов и итоговую статистику.

    Возвращает код выхода (0 при успехе).
    """

    cdx_client = CdxClient(
        timeout=args.timeout,
        user_agent="common-crawl-cli/1.0 (+https://commoncrawl.org/)",
    )
    warc_client = WARCClient(
        timeout=args.timeout,
        user_agent="common-crawl-cli/1.0 (+https://commoncrawl.org/)",
        delay=args.delay,
        snippet_chars=args.snippet_chars,
    )

    rows: list[list[str]] = []
    candidates: list[CdxRecord] = []
    skipped_domains: list[str] = []

    try:
        crawl_id = args.crawl or cdx_client.get_latest_crawl_id()

        # Собираем CDX-кандидатов по каждому домену.
        # --candidate-limit применяется к каждому домену отдельно.
        seen_urls: set[str] = set()

        domains_progress = tqdm(
            args.domains,
            desc="Запрос CDX",
            unit="домен",
            dynamic_ncols=True,
        )
        for domain in domains_progress:
            try:
                records = cdx_client.query_html(
                    crawl_id=crawl_id,
                    domain=domain,
                    limit=args.candidate_limit,
                )
            except CdxError as exc:
                tqdm.write(f"[warn] домен {domain!r} пропущен: {exc}")
                skipped_domains.append(domain)
                continue

            for record in records:
                if record.url in seen_urls:
                    continue
                seen_urls.add(record.url)
                candidates.append(record)
        domains_progress.close()

        # Ищем совпадения по объединённому списку кандидатов.
        # --limit ограничивает суммарное число найденных страниц.

        progress = tqdm(
            enumerate(candidates, start=1),
            total=len(candidates),
            desc="Проверка WARC",
            unit="стр",
            dynamic_ncols=True,
        )
        try:
            for index, candidate in progress:
                if len(rows) >= args.limit:
                    break
                progress.set_postfix(найдено=len(rows), refresh=False)
                try:
                    page = warc_client.fetch_page(candidate)
                except WARCError as exc:
                    tqdm.write(  # ← было print
                        f"[warn] WARC #{index} пропущен ({candidate.url}): {exc}",
                    )
                    continue

                match = find_matching_page(
                    page,
                    keywords=args.keywords,
                    snippet_chars=args.snippet_chars,
                )
                if match is None:
                    continue

                rows.append(
                    [
                        candidate.url,
                        candidate.archived_at,
                        match.title or "—",
                        match.snippet if args.show_text else "",
                    ]
                )
        finally:
            progress.close()
    finally:
        cdx_client.close()
        warc_client.close()

    if args.show_text:
        headers = ["URL", "Дата архивации", "Заголовок страницы", "Фрагмент текста"]
    else:
        headers = ["URL", "Дата архивации", "Заголовок страницы"]
        rows = [row[:3] for row in rows]

    if rows:
        print(tabulate(rows, headers=headers, tablefmt="github"))
    else:
        print("Совпадений не найдено.")

    print(
        f"\nИндекс: {crawl_id}. "
        f"Проверено CDX-кандидатов: {len(candidates)}. "
        f"Найдено: {len(rows)}."
    )
    if len(rows) < args.limit and len(candidates) >= args.candidate_limit:
        print(
            "Примечание: достигнут --candidate-limit. "
            "Для более глубокого поиска увеличьте его."
        )

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Точка входа CLI: разбирает аргументы и запускает run().

    Ловит CdxError/WARCError (возвращает код 2) и KeyboardInterrupt
    (возвращает код 130). Аргумент argv нужен для вызова из тестов
    или из Jupyter без реального sys.argv.
    """

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return run(args)
    except (CdxError, WARCError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nОстановлено пользователем.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
