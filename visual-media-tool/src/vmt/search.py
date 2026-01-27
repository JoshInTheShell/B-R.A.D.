from __future__ import annotations
from typing import List, Dict
from .providers.base import Provider, MediaResult
from .providers.pexels import PexelsProvider
from .providers.pixabay import PixabayProvider
from .providers.unsplash import UnsplashProvider
from .config import Settings

class MediaSearcher:
    def __init__(self, settings: Settings, enabled: Dict[str, bool] | None = None):
        self.settings = settings
        self.providers: List[Provider] = [
            PexelsProvider(settings.pexels_key),
            PixabayProvider(settings.pixabay_key),
            UnsplashProvider(settings.unsplash_key),
        ]
        self.enabled = enabled or {p.name: True for p in self.providers}

    def set_enabled(self, name: str, value: bool):
        self.enabled[name] = value

    def search_all(self, query: str, limit: int = 12) -> List[MediaResult]:
        results: List[MediaResult] = []
        for p in self.providers:
            if self.enabled.get(p.name, True):
                try:
                    results.extend(p.search(query, limit=limit))
                except Exception as e:
                    # Swallow provider errors but annotate a stub record
                    results.append(MediaResult(
                        provider=p.name, query=query,
                        title=f"[{p.name} error: {e}]", url="#", thumb="",
                        author=None, license=None, extra={"error": True}
                    ))
        return results
