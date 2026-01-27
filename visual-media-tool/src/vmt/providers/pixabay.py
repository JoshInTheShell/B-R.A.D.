from __future__ import annotations
import requests
from typing import List
from .base import Provider, MediaResult

class PixabayProvider(Provider):
    name = "Pixabay"

    def enabled(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, limit: int = 12) -> List[MediaResult]:
        if not self.enabled():
            return []
        url = "https://pixabay.com/api/"
        params = {"key": self.api_key, "q": query, "per_page": limit, "image_type": "photo"}
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        out = []
        for h in data.get("hits", []):
            out.append(MediaResult(
                provider=self.name, query=query,
                title=h.get("tags") or f"Pixabay {h.get('id')}",
                url=h.get("pageURL"),
                thumb=h.get("previewURL") or h.get("webformatURL"),
                author=h.get("user") or None,
                license="Pixabay License (see site)",
                extra={"id": h.get("id")}
            ))
        return out
