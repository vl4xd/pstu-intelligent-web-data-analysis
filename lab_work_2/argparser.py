import argparse
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
URLS_DIR = BASE_DIR / "urls"


def urls_txt(value: str) -> str:
    """
    Проверяет существование TXT-файла с исходными URL.
    Относительные пути ищутся в директории urls/.
    """

    path = Path(value)

    if not path.is_absolute():
        path = URLS_DIR / path

    path = path.resolve()

    if path.suffix.lower() != ".txt":
        raise argparse.ArgumentTypeError(
            "Файл должен иметь расширение .txt"
        )

    if not path.is_file():
        raise argparse.ArgumentTypeError(
            f"Файл не найден: {path}"
        )

    return str(path)


def non_negative_int(value: str) -> int:
    """Проверяет, что значение является целым числом >= 0."""

    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "Значение должно быть целым числом"
        )

    if number < 0:
        raise argparse.ArgumentTypeError(
            "Значение должно быть не меньше 0"
        )

    return number


def positive_limit(value: str) -> int:
    """Проверяет, что значение является целым числом >= 1."""

    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "Значение должно быть целым числом"
        )

    if number < 1:
        raise argparse.ArgumentTypeError(
            "Значение должно быть больше 0"
        )

    return number


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        prog="web-resource-graph",
        description=(
            "Сбор веб-ресурсов, извлечение ключевых терминов "
            "и построение интерактивного графа тематических связей."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog=(
            "Примеры использования:\n"
            "  py run.py metallurgy.txt\n"
            "  py run.py metallurgy.txt -d 1 -mp 50\n"
            "  py run.py metallurgy.txt -d 2 -mc 5\n"
            "  py run.py metallurgy.txt --no-use-cache"
        )
    )

    parser.add_argument(
        "dataurls",
        type=urls_txt,
        metavar="FILE",
        help=(
            "TXT-файл с исходными URL для обхода. "
            "Относительный путь указывается относительно директории urls/."
        )
    )

    parser.add_argument(
        "-d",
        "--deep",
        type=non_negative_int,
        default=0,
        metavar="N",
        help=(
            "Максимальная глубина обхода ссылок. "
            "0 — обрабатываются только начальные URL, "
            "1 — дополнительно первый уровень ссылок."
        )
    )

    parser.add_argument(
        "--use-cache",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Использовать JSON-кэш ранее обработанных страниц. "
            "Для принудительной повторной загрузки использовать --no-use-cache."
        )
    )

    parser.add_argument(
        "-mp",
        "--max-pages",
        type=positive_limit,
        default=25,
        metavar="N",
        help=(
            "Максимальное количество уникальных URL, "
            "которые будут обработаны за один запуск."
        )
    )

    parser.add_argument(
        "-mc",
        "--min-common",
        type=positive_limit,
        default=3,
        metavar="N",
        help=(
            "Минимальное количество общих ключевых терминов "
            "между двумя сайтами, необходимое для создания ребра графа."
        )
    )

    return parser