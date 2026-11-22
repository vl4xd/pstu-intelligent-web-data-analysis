import json
import re
from pathlib import Path

import nltk
import pandas as pd
import pymorphy3
from bs4 import BeautifulSoup
from nltk.corpus import stopwords

# --- Локальная папка для NLTK ---
NLTK_DATA_DIR = Path(__file__).parent / "nltk_data"
NLTK_DATA_DIR.mkdir(parents=True, exist_ok=True)
if str(NLTK_DATA_DIR) not in nltk.data.path:
    nltk.data.path.insert(0, str(NLTK_DATA_DIR))

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords", download_dir=str(NLTK_DATA_DIR), quiet=True)

morph = pymorphy3.MorphAnalyzer()

# --- Стоп-слова: базовые + кастомные + HTML ---
base_stopwords = set(stopwords.words("russian"))

custom_stopwords = {
    # Слова-паразиты из новостей
    "который", "это", "год", "мочь", "также", "каждый", "один", "новый",
    "свой", "весь", "человек", "вопрос", "почему", "самый", "такой",
    "наш", "ваш", "она", "они", "оно", "быть", "стать", "нужно",
    "можно", "надо", "если", "чтобы", "когда", "где", "куда", "откуда",
    "очень", "более", "менее", "сам", "этот", "тот", "всё",
    "статья", "проект", "задача", "работа", "работать", "решение",
    "также", "например", "кроме", "после", "перед", "через",
}

# HTML и его артефакты (главный источник мусора в товарах)
html_stopwords = {
    "nbsp", "div", "span", "strong", "em", "b", "i", "u", "p", "br",
    "table", "tbody", "thead", "tr", "td", "th", "ul", "ol", "li",
    "font", "style", "class", "href", "src", "img", "width", "height",
    "color", "size", "background", "align", "border", "body", "html",
    "amp", "quot", "lt", "gt", "apos", "middot", "mdash", "ndash",
    "hellip", "laquo", "raquo", "copy", "reg", "trade",
    # Немецкие/английские обрывки из товаров
    "guten", "morgen", "richard", "royal", "gold", "crystalite",
    "taller", "table", "tbody",
}

russian_stopwords = base_stopwords | custom_stopwords | html_stopwords


def clean_html_artifacts(text: str) -> str:
    """Удаляет HTML-теги, entities и мусор."""
    if not isinstance(text, str):
        return ""

    # 1. BeautifulSoup снимает все теги, оставляя текст
    text = BeautifulSoup(text, "html.parser").get_text(separator=" ")

    # 2. HTML-entities: &nbsp; &amp; и т.п.
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"&#\d+;", " ", text)

    # 3. Неразрывные пробелы
    text = text.replace("\xa0", " ")

    # 4. URL-ы
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"www\.\S+", " ", text)

    # 5. Одиночные символы
    text = re.sub(r"\b\w\b", " ", text)

    # 6. Многократные пробелы
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def preprocess_text(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return ""

    # Сначала — HTML-чистка
    text = clean_html_artifacts(text)

    # Потом — обычная очистка
    text = text.lower()
    text = re.sub(r"[^а-яёa-z\s]", " ", text)

    tokens = text.split()
    lemmas = []
    for token in tokens:
        if token in russian_stopwords:
            continue
        if len(token) < 3:
            continue
        lemma = morph.parse(token)[0].normal_form
        if lemma in russian_stopwords:
            continue
        lemmas.append(lemma)

    return " ".join(lemmas)


def load_and_prepare_data(filepath, text_columns, limit=None):
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {filepath}")

    if path.suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            df = pd.DataFrame(json.load(f))
    else:
        df = pd.read_csv(path)

    existing = [c for c in text_columns if c in df.columns]
    if not existing:
        raise ValueError(
            f"Колонки {text_columns} не найдены. Есть: {list(df.columns)}"
        )

    df["raw_text"] = df[existing].fillna("").astype(str).agg(" ".join, axis=1)
    df = df[df["raw_text"].str.strip().astype(bool)]
    if limit is not None:
        df = df.head(limit)

    print(f"Препроцессинг {len(df)} документов...")
    df["clean_text"] = df["raw_text"].apply(preprocess_text)
    df = df[df["clean_text"].str.strip().astype(bool)]

    texts = df["clean_text"].tolist()
    tokenized_texts = [t.split() for t in texts]
    print(f"После препроцессинга осталось: {len(texts)} документов")
    return texts, tokenized_texts