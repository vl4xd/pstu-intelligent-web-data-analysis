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
    title: str
    text: str


@dataclass(frozen=True)
class MatchData:
    title: str
    snippet: str


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "template", "svg"}:
            self._skip_depth += 1
        if tag == "title" and self._skip_depth == 0:
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript", "template", "svg"}:
            if self._skip_depth > 0:
                self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return

        if self._in_title:
            self.title_parts.append(data)

        self.text_parts.append(data)


def clean_text(value: str) -> str:
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def parse_html(html_bytes: bytes, encoding: str | None = None) -> PageData:
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
    def __init__(
        self,
        timeout: float = 30.0,
        user_agent: str = "common-crawl-cli/1.0",
        delay: float = 1.0,
        snippet_chars: int = 220,
    ) -> None:
        self.timeout = timeout
        self.delay = delay
        self.snippet_chars = snippet_chars
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self._last_request_at = 0.0

    def close(self) -> None:
        self.session.close()

    def _respect_delay(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.delay - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def fetch_page(self, record: CdxRecord) -> PageData:
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
    position = data.find(b"\r\n\r\n")
    if position >= 0:
        return position, 4

    position = data.find(b"\n\n")
    if position >= 0:
        return position, 2

    return -1, 0


def parse_headers(block: bytes) -> dict[str, str]:
    headers: dict[str, str] = {}
    text = block.decode("iso-8859-1", errors="replace")

    for line in re.split(r"\r?\n", text):
        if not line or ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip()] = value.strip()

    return headers


def extract_charset(content_type: str) -> str | None:
    match = re.search(r"charset=([^\s;]+)", content_type, re.IGNORECASE)
    if not match:
        return None

    return match.group(1).strip("\"'")


def parse_http_payload(payload: bytes, encoding: str | None = None) -> PageData:
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
