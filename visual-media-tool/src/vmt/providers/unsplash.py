from __future__ import annotations
import requests
from typing import List
from .base import Provider, MediaResult

class UnsplashProvider(Provider):
    name = "Unsplash"

    def enabled(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, limit: int = 12) -> List[MediaResult]:
        if not self.enabled():
            return []
        url = "https://api.unsplash.com/search/photos"
        hdrs = {"Authorization": f"Client-ID {self.api_key}"}
        params = {"query": query, "per_page": limit}
        r = requests.get(url, headers=hdrs, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        out = []
        for it in data.get("results", []):
            title = (it.get("alt_description") or it.get("description") or f"Unsplash {it.get('id')}")
            thumb = (it.get("urls", {}) or {}).get("small") or (it.get("urls", {}) or {}).get("thumb")
            author = (it.get("user", {}) or {}).get("name")
            out.append(MediaResult(
                provider=self.name, query=query,
                title=title, url=it.get("links", {}).get("html"),
                thumb=thumb, author=author,
                license="Unsplash License (attribution required)",
                extra={"id": it.get("id")}
            ))
        return out
