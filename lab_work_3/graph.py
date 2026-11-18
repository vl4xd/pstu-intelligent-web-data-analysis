from pathlib import Path

from pyvis.network import Network
from models.article import Article


class GraphError(Exception):
    """Ошибка при построении графа."""
    pass


class ArticleGraph:
    """Построение графа связей между статьями Википедии."""

    def __init__(self):
        self.network = Network(
            height="800px",
            width="100%",
            directed=True,
            bgcolor="#ffffff",
            font_color="#222222"
        )

        # Настройки физики графа
        self.network.barnes_hut(
            gravity=-30000,
            central_gravity=0.3,
            spring_length=150,
            spring_strength=0.04,
            damping=0.09
        )

        self.added_nodes = set()
        self.added_edges = set()

    def add_articles(self, articles: list[Article]) -> None:
        """Добавляет статьи и связи между ними."""

        if not articles:
            raise GraphError("Список статей пуст.")

        # Создаём множество названий собранных статей
        article_titles = {
            article.title.casefold()
            for article in articles
        }

        # Словарь для получения оригинального названия
        title_map = {
            article.title.casefold(): article.title
            for article in articles
        }

        # Добавляем узлы
        for article in articles:

            title = article.title

            if title in self.added_nodes:
                continue

            self.network.add_node(
                title,
                label=title,
                title=(
                    f"<b>{title}</b><br>"
                    f"Язык: {article.language}<br>"
                    f"Ссылка: {article.url}"
                ),
                url=article.url,
                shape="dot",
                size=20,
                color={
                    "background": "#4A90E2",
                    "border": "#245580",
                    "highlight": {
                        "background": "#F5A623",
                        "border": "#C47F0A"
                    }
                }
            )

            self.added_nodes.add(title)

        # Добавляем рёбра
        for article in articles:

            source = article.title

            for link in article.links:

                normalized_link = link.casefold()

                # Добавляем связь только между собранными статьями
                if normalized_link not in article_titles:
                    continue

                target = title_map[normalized_link]

                if source == target:
                    continue

                edge = (source, target)

                if edge in self.added_edges:
                    continue

                self.network.add_edge(
                    source,
                    target,
                    arrows="to",
                    color="#999999"
                )

                self.added_edges.add(edge)

    def save(self, filepath: str) -> None:
        """Сохраняет граф в HTML."""

        path = Path(filepath)

        try:
            path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            self.network.write_html(
                str(path),
                open_browser=False
            )

            print(
                f"[УСПЕХ] Граф сохранён: "
                f"{path.resolve()}"
            )

        except (OSError, ValueError, TypeError) as error:
            raise GraphError(
                f"Не удалось сохранить граф: {error}"
            ) from error

    def save_dot(self, filepath: str) -> None:
        """Сохраняет граф связей в формате DOT."""

        path = Path(filepath)

        try:
            path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            with path.open("w", encoding="utf-8") as file:

                file.write("digraph WikimediaGraph {\n")

                file.write('    rankdir="LR";\n')
                file.write('    node [shape=box, style=rounded];\n\n')

                # Записываем все узлы
                for node in self.added_nodes:
                    safe_node = node.replace("\\", "\\\\").replace('"', '\\"')
                    file.write(f'    "{safe_node}";\n')

                file.write("\n")

                # Записываем все связи
                for source, target in self.added_edges:

                    safe_source = (
                        source.replace("\\", "\\\\")
                        .replace('"', '\\"')
                    )

                    safe_target = (
                        target.replace("\\", "\\\\")
                        .replace('"', '\\"')
                    )

                    file.write(
                        f'    "{safe_source}" -> "{safe_target}";\n'
                    )

                file.write("}\n")

            print(
                f"[УСПЕХ] DOT-граф сохранён: "
                f"{path.resolve()}"
            )

        except OSError as error:
            raise GraphError(
                f"Не удалось сохранить DOT-граф: {error}"
            ) from error


def build_graph(
    articles: list[Article],
    filepath: str = "output/graph.html"
) -> None:
    """Создаёт HTML- и DOT-графы."""

    graph = ArticleGraph()

    graph.add_articles(articles)

    # Сохраняем интерактивный HTML-граф
    graph.save(filepath)

    # Формируем путь для DOT
    dot_filepath = str(
        Path(filepath).with_suffix(".dot")
    )

    # Сохраняем DOT-граф
    graph.save_dot(dot_filepath)

    print("\n" + "=" * 40)
    print("РЕЗУЛЬТАТ ПОСТРОЕНИЯ ГРАФА")
    print("=" * 40)

    print(f"Количество узлов: {len(graph.added_nodes)}")
    print(f"Количество связей: {len(graph.added_edges)}")

    if len(graph.added_nodes) >= 30:
        print("[УСПЕХ] Минимум 30 статей собрано.")
    else:
        print(
            "[ПРЕДУПРЕЖДЕНИЕ] "
            "Для выполнения требования необходимо "
            "минимум 30 статей."
        )

