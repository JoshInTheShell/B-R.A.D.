from __future__ import annotations
import requests
from typing import List
from .base import Provider, MediaResult, MediaType

class PixabayProvider(Provider):
    name = "Pixabay"

    def enabled(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, limit: int = 12, media_type: MediaType = "photo") -> List[MediaResult]:
        if not self.enabled():
            return []
        
        # Pixabay uses same endpoint but different parameters
        url = "https://pixabay.com/api/"
        
        if media_type == "video":
            url = "https://pixabay.com/api/videos/"
            params = {
                "key": self.api_key,
                "q": query,
                "per_page": limit,
                "video_type": "all"  # film, animation, or all
            }
        else:
            params = {
                "key": self.api_key,
                "q": query,
                "per_page": limit,
                "image_type": "photo"
            }
        
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"Pixabay API error: {e}")
            return []
        
        out = []
        
        if media_type == "video":
            # Handle video results
            for v in data.get("hits", []):
                # Parse video files from Pixabay's structure
                video_files = {}
                videos = v.get("videos", {})
                for quality_key in ["large", "medium", "small", "tiny"]:
                    if quality_key in videos and "url" in videos[quality_key]:
                        video_files[quality_key] = videos[quality_key]["url"]
                
                out.append(MediaResult(
                    provider=self.name,
                    query=query,
                    title=v.get("tags") or f"Pixabay Video {v.get('id')}",
                    url=v.get("pageURL"),
                    thumb=v.get("userImageURL") or "",  # User avatar as fallback
                    media_type="video",
                    author=v.get("user"),
                    license="Pixabay License (free to use)",
                    duration=v.get("duration"),
                    video_files=video_files,
                    extra={
                        "id": v.get("id"),
                        "type": v.get("type"),
                        "picture_id": v.get("picture_id")
                    }
                ))
        else:
            # Handle photo results
            for h in data.get("hits", []):
                out.append(MediaResult(
                    provider=self.name,
                    query=query,
                    title=h.get("tags") or f"Pixabay {h.get('id')}",
                    url=h.get("pageURL"),
                    thumb=h.get("previewURL") or h.get("webformatURL"),
                    media_type="photo",
                    author=h.get("user"),
                    license="Pixabay License (free to use)",
                    extra={
                        "id": h.get("id"),
                        "largeImageURL": h.get("largeImageURL"),
                        "webformatURL": h.get("webformatURL")
                    }
                ))
        
        return out
