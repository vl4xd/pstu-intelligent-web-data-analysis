from dataclasses import dataclass, asdict


@dataclass
class Article:
    title: str
    language: str
    url: str
    text: str
    links: list[str]

    def to_dict(self) -> dict:
        """Преобразование статьи в словарь для JSON."""
        return asdict(self)