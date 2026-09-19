from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import gzip
import html
import re
import time
from html.parser import HTMLParser

import requests
from cdx import CdxRecord


DATA_BASE_URL = "https://data.commoncrawl.org"


class WARCError(RuntimeError):
    """Ошибка получения или разбора WARC."""


@dataclass(frozen=True)
class PageData:
    """Извлечённые из HTML-страницы заголовок и видимый текст."""
    
    title: str
    text: str


@dataclass(frozen=True)
class MatchData:
    """Результат поиска ключевых слов: заголовок и фрагмент текста."""

    title: str
    snippet: str


class _VisibleTextParser(HTMLParser):
    """HTMLParser, собирающий title и видимый текст страницы.

    Пропускает содержимое script, style, noscript, template, svg.
    Складывает текст из <title> отдельно (title_parts), остальной
    видимый текст — в text_parts.
    """

    def __init__(self) -> None:
        """Инициализирует счётчик пропуска и списки для title/текста."""

        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Обрабатывает открывающий тег: включает skip или входит в <title>."""

        tag = tag.lower()
        if tag in {"script", "style", "noscript", "template", "svg"}:
            self._skip_depth += 1
        if tag == "title" and self._skip_depth == 0:
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        """Обрабатывает закрывающий тег: выключает skip или выходит из <title>."""

        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript", "template", "svg"}:
            if self._skip_depth > 0:
                self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        """Сохраняет текстовые данные, пропуская содержимое script/style и пр."""

        if self._skip_depth > 0:
            return

        if self._in_title:
            self.title_parts.append(data)

        self.text_parts.append(data)


def clean_text(value: str) -> str:
    """Сохраняет текстовые данные, пропуская содержимое script/style и пр."""

    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def parse_html(html_bytes: bytes, encoding: str | None = None) -> PageData:
    """Парсит байты HTML и возвращает заголовок и видимый текст.

    Пытается декодировать сначала указанной кодировкой (если задана),
    затем utf-8, windows-1251, latin-1. Ошибки декодирования заменяются
    символом-заменителем. Возвращает PageData(title=..., text=...).
    """

    encodings = []
    if encoding:
        encodings.append(encoding)
    encodings.extend(["utf-8", "windows-1251", "latin-1"])

    decoded: str | None = None
    for candidate in encodings:
        try:
            decoded = html_bytes.decode(candidate, errors="replace")
            break
        except LookupError:
            continue

    if decoded is None:
        decoded = html_bytes.decode("utf-8", errors="replace")

    parser = _VisibleTextParser()
    parser.feed(decoded)
    parser.close()

    return PageData(
        title=clean_text(" ".join(parser.title_parts)),
        text=clean_text(" ".join(parser.text_parts)),
    )


class WARCClient:
    """Клиент для точечной загрузки и разбора WARC-записей.

    Использует HTTP Range-запросы к data.commoncrawl.org, чтобы скачать
    ровно один capture по offset/length из CDX. Между запросами выдерживает
    паузу delay, чтобы не провоцировать rate limit.
    """

    def __init__(
        self,
        timeout: float = 30.0,
        user_agent: str = "common-crawl-cli/1.0",
        delay: float = 1.0,
        snippet_chars: int = 220,
    ) -> None:
        """Сохраняет настройки и создаёт HTTP-сессию."""
        
        self.timeout = timeout
        self.delay = delay
        self.snippet_chars = snippet_chars
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self._last_request_at = 0.0

    def close(self) -> None:
        """Закрывает HTTP-сессию и освобождает ресурсы."""

        self.session.close()

    def _respect_delay(self) -> None:
        """Спит столько, чтобы между запросами прошло не меньше delay секунд."""

        elapsed = time.monotonic() - self._last_request_at
        remaining = self.delay - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def fetch_page(self, record: CdxRecord) -> PageData:
        """Скачивает один WARC-record по Range и возвращает PageData.

        Делает GET с заголовком Range на основе record.offset/length,
        проверяет код 206, Content-Range и размер ответа, затем
        распаковывает gzip и извлекает HTML. При любой проблеме
        бросает WARCError.
        """

        self._respect_delay()

        start = record.offset
        end = record.offset + record.length - 1
        url = f"{DATA_BASE_URL}/{record.filename}"

        try:
            response = self.session.get(
                url,
                headers={"Range": f"bytes={start}-{end}"},
                timeout=self.timeout,
            )
            self._last_request_at = time.monotonic()
        except requests.RequestException as exc:
            self._last_request_at = time.monotonic()
            raise WARCError(f"Ошибка загрузки WARC: {exc}") from exc

        if response.status_code != 206:
            raise WARCError(
                f"Common Crawl не вернул HTTP 206 для Range-запроса "
                f"(получено {response.status_code})."
            )

        content_range = response.headers.get("Content-Range", "")
        expected_range = f"bytes {start}-{end}/"
        if not content_range.startswith(expected_range):
            raise WARCError(
                "Получен неожиданный Content-Range: "
                f"{content_range!r}, ожидался диапазон {start}-{end}."
            )

        if len(response.content) != record.length:
            raise WARCError(
                f"Размер WARC-ответа {len(response.content)} байт, "
                f"ожидалось {record.length}."
            )

        try:
            return parse_warc_response(
                response.content,
                encoding=None,
            )
        except Exception as exc:
            raise WARCError(
                f"Не удалось разобрать WARC record для {record.url}: {exc}"
            ) from exc


def parse_warc_response(data: bytes, encoding: str | None = None) -> PageData:
    """Распаковывает один gzip-сжатый WARC record и извлекает HTTP payload.

    Common Crawl CDX возвращает offset/length ровно для одной WARC capture,
    поэтому отдельная полноценная потоковая WARC-библиотека здесь не обязательна.
    """
    try:
        decompressed = gzip.decompress(data)
    except OSError as exc:
        raise WARCError(f"gzip decoding error: {exc}") from exc

    header_end, separator_length = find_header_end(decompressed)
    if header_end < 0:
        raise WARCError("WARC record не содержит корректного заголовочного блока.")

    header_block = decompressed[:header_end]
    payload = decompressed[header_end + separator_length :]

    warc_headers = parse_headers(header_block)
    if warc_headers.get("WARC-Type", "").lower() != "response":
        raise WARCError(
            f"Ожидался WARC-Type: response, "
            f"получено: {warc_headers.get('WARC-Type', 'unknown')!r}"
        )

    content_length = warc_headers.get("Content-Length")
    if content_length:
        try:
            expected_length = int(content_length)
        except ValueError as exc:
            raise WARCError("Некорректный WARC Content-Length.") from exc

        payload = payload[:expected_length]

    return parse_http_payload(payload, encoding)


def find_header_end(data: bytes) -> tuple[int, int]:
    """Ищет конец блока заголовков (пустую строку).

    Возвращает (позиция, длина разделителя): 4 для CRLFCRLF,
    2 для LFLF или (-1, 0), если разделитель не найден.
    """

    position = data.find(b"\r\n\r\n")
    if position >= 0:
        return position, 4

    position = data.find(b"\n\n")
    if position >= 0:
        return position, 2

    return -1, 0


def parse_headers(block: bytes) -> dict[str, str]:
    """Парсит блок HTTP/WARC-заголовков в словарь name -> value.

    Декодирует как latin-1 (безопасно для любых байт), игнорирует
    пустые строки и строки без двоеточия.
    """

    headers: dict[str, str] = {}
    text = block.decode("iso-8859-1", errors="replace")

    for line in re.split(r"\r?\n", text):
        if not line or ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip()] = value.strip()

    return headers


def extract_charset(content_type: str) -> str | None:
    """Извлекает значение charset из заголовка Content-Type.

    Возвращает имя кодировки без кавычек или None, если charset не указан.
    """

    match = re.search(r"charset=([^\s;]+)", content_type, re.IGNORECASE)
    if not match:
        return None

    return match.group(1).strip("\"'")


def parse_http_payload(payload: bytes, encoding: str | None = None) -> PageData:
    """Отделяет HTTP-заголовки от тела и парсит HTML.

    Ищет пустую строку (CRLFCRLF или LFLF) как разделитель. Если её нет,
    считает, что весь payload — это тело. Возвращает PageData.
    """

    header_end = payload.find(b"\r\n\r\n")
    separator_length = 4

    if header_end < 0:
        header_end = payload.find(b"\n\n")
        separator_length = 2

    if header_end >= 0:
        body = payload[header_end + separator_length :]
    else:
        body = payload

    return parse_html(body, encoding)


def find_matching_page(
    page: PageData,
    keywords: list[str],
    snippet_chars: int = 220,
) -> MatchData | None:
    """Проверяет, что на странице есть все ключевые слова.

    Ищет каждое ключевое слово как подстроку в склейке title + text
    (регистронезависимо). Если хотя бы одного слова нет — возвращает None.
    Иначе возвращает MatchData с заголовком и фрагментом вокруг
    первого найденного совпадения.
    """
    
    terms = [clean_text(term).casefold() for term in keywords if clean_text(term)]
    if not terms:
        return None

    searchable = clean_text(
        f"{page.title}. {page.text}"
    )
    folded = searchable.casefold()

    positions: list[int] = []
    for term in terms:
        position = folded.find(term)
        if position < 0:
            return None
        positions.append(position)

    first = min(positions)
    snippet = make_snippet(searchable, first, snippet_chars)

    return MatchData(
        title=page.title,
        snippet=snippet,
    )


def make_snippet(text: str, match_start: int, max_chars: int) -> str:
    """Возвращает фрагмент текста вокруг позиции совпадения.

    Берёт max_chars символов, стараясь захватить немного контекста
    перед совпадением (примерно треть длины). Добавляет многоточия
    по краям, если фрагмент обрезан. Если текст короче max_chars —
    возвращает его целиком.
    """

    if len(text) <= max_chars:
        return text

    context_before = max_chars // 3
    start = max(0, match_start - context_before)
    end = min(len(text), start + max_chars)

    if end - start < max_chars:
        start = max(0, end - max_chars)

    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""

    return f"{prefix}{text[start:end].strip()}{suffix}"
