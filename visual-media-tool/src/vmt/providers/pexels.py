from __future__ import annotations
import requests
from typing import List
from .base import Provider, MediaResult

class PexelsProvider(Provider):
    name = "Pexels"

    def enabled(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, limit: int = 12) -> List[MediaResult]:
        if not self.enabled():
            return []
        url = "https://api.pexels.com/v1/search"
        hdrs = {"Authorization": self.api_key}
        params = {"query": query, "per_page": limit}
        r = requests.get(url, headers=hdrs, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        out = []
        for p in data.get("photos", []):
            out.append(MediaResult(
                provider=self.name, query=query,
                title=p.get("alt") or f"Pexels {p.get('id')}",
                url=p.get("url"),
                thumb=p.get("src", {}).get("medium") or p.get("src", {}).get("small"),
                author=(p.get("photographer") or None),
                license="Free to use (see Pexels license)",
                extra={"id": p.get("id")}
            ))
        return out
