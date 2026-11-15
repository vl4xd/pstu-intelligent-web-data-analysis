from pathlib import Path
from pyvis.network import Network
import webbrowser


BASE_DIR = Path(__file__).resolve().parent


net = Network(
    height="750px",
    width="100%",
    directed=False,
    cdn_resources="in_line"
)

net.add_node(1, label="Сайт 1")
net.add_node(2, label="Сайт 2")
net.add_node(3, label="Сайт 3")

net.add_edge(1, 2, title="5 общих терминов")
net.add_edge(2, 3, title="8 общих терминов")

# Сохраняем HTML и открываем браузер.
output_path = BASE_DIR / "test_graph.html"

# Генерируем HTML
html = net.generate_html(notebook=False)

# Сохраняем с кодировкой UTF-8
output_path.write_text(
    html,
    encoding="utf-8"
)

# Открываем в браузере
webbrowser.open(output_path.resolve().as_uri())

print(f"Граф сохранён: {output_path}")