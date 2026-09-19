# Практика 1: Конскольное приложение "Common Crawl"

**Автор:** Платонов Владислав, АСУ8-25-1м

CLI-приложение на Python для поиска ключевых слов в HTML-страницах архива [Common Crawl](https://commoncrawl.org/).

Приложение использует два шага:

1. **CDXJ index** — получает список HTML-captures для заданного домена и необходимые координаты WARC: `filename`, `offset`, `length`.
2. **WARC Range request** — точечно запрашивает только нужный диапазон байт из `data.commoncrawl.org`, распаковывает запись и ищет ключевые слова в тексте страницы.

Это соответствует официальной схеме Common Crawl: CDXJ содержит URL и метаданные capture, а для чтения самой страницы используется HTTP Range-запрос по `filename`/`offset`/`length`.

## Возможности

- Python + `argparse`;
- стандартная библиотека для gzip/WARC parsing без отдельной WARC-зависимости;
- поиск по одному или нескольким ключевым словам;
- фильтр по домену;
- ограничение числа результатов, по умолчанию `10`;
- `--show-text` для фрагмента текста страницы;
- автоматический выбор последнего Common Crawl индекса;
- явный выбор индекса через `--crawl`;
- ограничение числа WARC-кандидатов через `--candidate-limit`;
- вывод через `tabulate`;
- последовательные запросы с паузой, чтобы не создавать лишнюю нагрузку на CDX API.

## Структура

```text
common-crawl-cli/
├── .gitignore
├── app.py
├── cdx.py
├── example.ipynb
├── README.md
├── requirements.txt
└── warc.py
```

### `app.py`

Отвечает за CLI-интерфейс:

- `argparse`;
- валидацию аргументов;
- поиск;
- форматирование результата через `tabulate`.

### `cdx.py`

Отвечает за CDXJ:

- получение списка доступных crawl индексов;
- определение последнего индекса;
- запрос HTML-captures домена;
- разбор CDX JSONL в `CdxRecord`.

### `warc.py`

Отвечает за WARC:

- HTTP Range request;
- проверку `206 Partial Content` и `Content-Range`;
- распаковку gzip;
- разбор WARC response;
- извлечение HTML title и видимого текста;
- проверку ключевых слов;
- построение snippet.

## Установка

Требуется Python 3.10+.

### Windows

Откройте PowerShell:

```bash
git clone <URL-репозитория>
```

```bash
cd lab_work_1
```

```bash
python -m venv .venv
```

```bash
source .venv/Scripts/activate
```

```bash
python -m pip install --upgrade pip
```

```bash
python -m python -m pip install -r requirements.txt
```

Запуск:

```bash
python app.py python -d example.com
```

С фрагментом текста:

```bash
python app.py python language -d example.com --show-text
```

### macOS

Терминал:

```bash
git clone <URL-репозитория>
cd common-crawl-cli

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m python -m pip install -r requirements.txt
```

Запуск:

```bash
python app.py python -d example.com
```

### Linux

Терминал:

```bash
git clone <URL-репозитория>
cd common-crawl-cli

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m python -m pip install -r requirements.txt
```

Запуск:

```bash
python app.py python -d example.com
```

Для Debian/Ubuntu при отсутствии `venv`:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

## Использование

Базовый запуск:

```bash
python app.py "machine learning" -d example.com
```

Два условия поиска. По умолчанию **все** указанные термы должны находиться на странице:

```bash
python app.py python asyncio -d docs.python.org
```

Ограничение результатов:

```bash
python app.py python -d docs.python.org --limit 5
```

Показать фрагмент:

```bash
python app.py python -d docs.python.org --show-text
```

Указать конкретный crawl:

```bash
python app.py python -d docs.python.org --crawl CC-MAIN-2026-34
```

Увеличить глубину просмотра CDX-кандидатов:

```bash
python app.py python -d docs.python.org --candidate-limit 2000
```

Изменить паузу между запросами:

```bash
python app.py python -d docs.python.org --delay 2
```

## Аргументы

```text
usage: common-crawl-search  [-h] -d DOMAIN [-l N] [--show-text] [--crawl CRAWL]
                            [--candidate-limit N] [--timeout SECONDS]
                            [--delay SECONDS] [--snippet-chars N]
                            keywords [keywords ...]
```

| Аргумент | Назначение |
|---|---|
| `keywords` | одно или несколько ключевых слов/фраз |
| `-d, --domain` | домен поиска, включая его поддомены |
| `-l, --limit` | максимальное число найденных страниц, default `10` |
| `--show-text` | показать snippet |
| `--crawl` | конкретный индекс `CC-MAIN-YYYY-WW`; по умолчанию — последний |
| `--candidate-limit` | сколько CDX-записей максимум проверять по содержимому |
| `--timeout` | HTTP timeout |
| `--delay` | пауза между сетевыми запросами |
| `--snippet-chars` | размер snippet |

## Формат результата

Без `--show-text`:

```text
| URL                         | Дата архивации        | Заголовок страницы | Фрагмент текста (опц.) |
|-----------------------------|-----------------------|--------------------|------------------------|
| https://example.com/about   | 2026-08-10 10:20:30 UTC | About Example      |                        |
```

С `--show-text`:

```text
| URL                         | Дата архивации        | Заголовок страницы | Фрагмент текста |
|-----------------------------|-----------------------|--------------------|-----------------|
| https://example.com/about   | 2026-08-10 10:20:30 UTC | About Example      | …machine learning is... |
```

## Почему `--domain` обязателен

CDXJ — это индекс captures/URL и WARC-координат, а не индекс полнотекстового содержимого страницы. Поэтому поиск произвольного слова по всему Common Crawl означал бы фактически масштабное сканирование WARC.

В этой реализации домен обязателен, чтобы запросы были предсказуемыми по объёму:

```text
CDX (domain) -> N кандидатов -> Range WARC -> HTML -> поиск keywords
```

Это существенно практичнее, чем пытаться сканировать весь crawl.

Если нужен именно глобальный поиск по миллиардам страниц, правильнее перейти к аналитическому варианту с Common Crawl URL Index/Parquet + Athena/Spark/DuckDB и уже затем точечно читать WARC.