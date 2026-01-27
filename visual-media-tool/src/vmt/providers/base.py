from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any
import abc

@dataclass
class MediaResult:
    provider: str
    query: str
    title: str
    url: str
    thumb: str
    author: str | None = None
    license: str | None = None
    extra: dict | None = None

class Provider(abc.ABC):
    name: str

    def __init__(self, api_key: str | None):
        self.api_key = api_key

    @abc.abstractmethod
    def enabled(self) -> bool: ...

    @abc.abstractmethod
    def search(self, query: str, limit: int = 12) -> List[MediaResult]: ...
