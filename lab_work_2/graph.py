
from collections.abc import Iterable, Mapping
from datetime import datetime
from html import escape
from pathlib import Path
import webbrowser

from pyvis.network import Network


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"


def build_graph(
    site_terms: Mapping[str, Iterable[str]],
    min_common_terms: int = 3,
    output_dir: Path = RESULTS_DIR,
    open_browser: bool = True
) -> Path:
    """
    Строит интерактивный граф связей между сайтами.

    Args:
        site_terms: Словарь {домен: множество терминов}.
        min_common_terms: Минимальное количество общих терминов
                          для создания ребра.
        output_dir: Директория сохранения HTML.
        open_browser: Открывать ли граф в браузере.

    Returns:
        Path: Путь к созданному HTML-файлу.
    """

    # Проверяем входные параметры.
    if min_common_terms < 1:
        raise ValueError(
            "min_common_terms должен быть >= 1"
        )

    if not site_terms:
        raise ValueError(
            "Нет данных для построения графа"
        )

    # Нормализуем входные данные.
    normalized_terms = {}

    for domain, terms in site_terms.items():

        domain = str(domain).strip()

        if not domain:
            continue

        normalized_terms[domain] = {
            str(term).strip()
            for term in terms
            if term and str(term).strip()
        }

    if not normalized_terms:
        raise ValueError(
            "Нет корректных сайтов для построения графа"
        )

    # Создаём интерактивный граф.
    net = Network(
        height="850px",
        width="100%",
        directed=False,
        bgcolor="#ffffff",
        font_color="#222222",
        cdn_resources="in_line"
    )

    # Настраиваем физику графа.
    net.barnes_hut()

    # Включаем панель настройки физики.
    net.show_buttons(filter_=["physics"])

    # Добавляем узлы.
    for domain, terms in normalized_terms.items():

        terms_count = len(terms)

        net.add_node(
            domain,
            label=domain,
            title=(
                f"{domain}\n"
                f"Уникальных терминов: {terms_count}"
            ),
            value=max(1, terms_count),
            shape="dot"
        )

    # Сравниваем все пары сайтов.
    domains = list(normalized_terms.keys())

    for i in range(len(domains)):

        for j in range(i + 1, len(domains)):

            site1 = domains[i]
            site2 = domains[j]

            terms1 = normalized_terms[site1]
            terms2 = normalized_terms[site2]

            # Находим пересечение множеств.
            common_terms = terms1 & terms2

            common_count = len(common_terms)

            # Проверяем минимальное количество общих терминов.
            if common_count < min_common_terms:
                continue

            # Формируем подсказку для ребра.
            sorted_terms = sorted(common_terms)

            preview = sorted_terms[:50]

            tooltip = (
                f"{site1} ↔ {site2}\n"
                f"Общих терминов: {common_count}\n\n"
                f"Общие термины:\n"
                + "\n".join(preview)
            )

            if common_count > 50:
                tooltip += (
                    f"<br>... и ещё {common_count - 50} терминов"
                )

            # Добавляем ребро.
            net.add_edge(
                site1,
                site2,
                value=common_count,
                title=tooltip,
                label=f"{common_count}"
            )

    # Создаём директорию результатов.
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # Генерируем уникальное имя файла.
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    output_path = output_dir / f"graph_{timestamp}.html"

    # Генерируем HTML вне режима Jupyter.
    html = net.generate_html(notebook=False)

    # Сохраняем HTML в UTF-8.
    output_path.write_text(
        html,
        encoding="utf-8"
    )

    # Открываем результат в браузере.
    if open_browser:
        webbrowser.open_new_tab(
            output_path.resolve().as_uri()
        )

    # Выводим статистику.
    print("\nГраф успешно создан!")
    print(f"Количество узлов: {len(net.nodes)}")
    print(f"Количество рёбер: {len(net.edges)}")
    print(f"Минимум общих терминов: {min_common_terms}")
    print(f"Файл: {output_path.resolve()}")

    return output_path


# Демонстрационный запуск.
if __name__ == "__main__":

    demo_terms = {
        "example.com": {
            "сталь",
            "металл",
            "производство",
            "сплав"
        },

        "example.org": {
            "сталь",
            "металл",
            "сплав",
            "промышленность"
        },

        "example.net": {
            "нефть",
            "газ",
            "добыча"
        },

        "example.ru": {
            "металл",
            "производство",
            "сталь"
        }
    }

    build_graph(
        site_terms=demo_terms,
        min_common_terms=2
    )
