from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Literal
import abc

MediaType = Literal["photo", "video"]

@dataclass
class MediaResult:
    provider: str
    query: str
    title: str
    url: str
    thumb: str
    media_type: MediaType  # Added to track if it's photo or video
    author: str | None = None
    license: str | None = None
    extra: dict | None = None
    # For videos, we'll store additional info
    duration: int | None = None  # duration in seconds
    video_files: dict | None = None  # video file URLs by quality

class Provider(abc.ABC):
    name: str

    def __init__(self, api_key: str | None):
        self.api_key = api_key

    @abc.abstractmethod
    def enabled(self) -> bool: ...

    @abc.abstractmethod
    def search(self, query: str, limit: int = 12, media_type: MediaType = "photo") -> List[MediaResult]: ...
