from __future__ import annotations
import requests
from typing import List
from .base import Provider, MediaResult, MediaType

class PexelsProvider(Provider):
    name = "Pexels"

    def enabled(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, limit: int = 12, media_type: MediaType = "photo") -> List[MediaResult]:
        if not self.enabled():
            return []
        
        # Use different endpoints for photos vs videos
        if media_type == "video":
            url = "https://api.pexels.com/videos/search"
        else:
            url = "https://api.pexels.com/v1/search"
        
        hdrs = {"Authorization": self.api_key}
        params = {"query": query, "per_page": limit}
        
        try:
            r = requests.get(url, headers=hdrs, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"Pexels API error: {e}")
            return []
        
        out = []
        
        if media_type == "video":
            # Handle video results
            for v in data.get("videos", []):
                # Get video files organized by quality
                video_files = {}
                for vf in v.get("video_files", []):
                    quality = vf.get("quality", "unknown")
                    if quality not in video_files:  # Keep first of each quality
                        video_files[quality] = vf.get("link")
                
                # Get best thumbnail
                thumb = None
                video_pictures = v.get("video_pictures", [])
                if video_pictures:
                    thumb = video_pictures[0].get("picture")
                
                out.append(MediaResult(
                    provider=self.name,
                    query=query,
                    title=f"Pexels Video {v.get('id')}",
                    url=v.get("url"),  # Link to Pexels page
                    thumb=thumb or "",
                    media_type="video",
                    author=v.get("user", {}).get("name"),
                    license="Free to use (Pexels license)",
                    duration=v.get("duration"),
                    video_files=video_files,
                    extra={
                        "id": v.get("id"),
                        "width": v.get("width"),
                        "height": v.get("height"),
                        "image": v.get("image")  # Alternative thumbnail
                    }
                ))
        else:
            # Handle photo results
            for p in data.get("photos", []):
                out.append(MediaResult(
                    provider=self.name,
                    query=query,
                    title=p.get("alt") or f"Pexels {p.get('id')}",
                    url=p.get("url"),
                    thumb=p.get("src", {}).get("medium") or p.get("src", {}).get("small"),
                    media_type="photo",
                    author=p.get("photographer"),
                    license="Free to use (Pexels license)",
                    extra={
                        "id": p.get("id"),
                        "src": p.get("src")  # All size variants
                    }
                ))
        
        return out
