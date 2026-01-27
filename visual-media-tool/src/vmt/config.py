import os
from dataclasses import dataclass

@dataclass
class Settings:
    pexels_key: str | None = None
    pixabay_key: str | None = None
    unsplash_key: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            pexels_key=os.getenv("PEXELS_API_KEY"),
            pixabay_key=os.getenv("PIXABAY_API_KEY"),
            unsplash_key=os.getenv("UNSPLASH_ACCESS_KEY"),
        )
