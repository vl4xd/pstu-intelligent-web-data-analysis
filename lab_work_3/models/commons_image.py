
from dataclasses import dataclass, asdict


@dataclass
class CommonsImage:
    title: str
    article_title: str
    image_url: str
    page_url: str
    description: str
    author: str
    license: str

    def to_dict(self) -> dict:
        return asdict(self)
