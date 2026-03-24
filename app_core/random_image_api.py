from __future__ import annotations

import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

from .config import CACHE_DIR, RANDOM_API_URL


class RandomImageAPI:
    def __init__(self, api_url: str = RANDOM_API_URL, target_dir: Path = CACHE_DIR) -> None:
        self.api_url = api_url
        self.target_dir = target_dir
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def fetch_image(self) -> Optional[Path]:
        timestamp = int(time.time())
        target = self.target_dir / f"random_{timestamp}.jpg"
        request_url = f"{self.api_url}?t={timestamp}"

        request = urllib.request.Request(
            request_url,
            headers={"User-Agent": "Mirage/1.1"},
        )

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                target.write_bytes(response.read())
            return target
        except Exception as error:
            print(f"[Mirage] Failed to fetch random image: {error}", file=sys.stderr)
            return None
