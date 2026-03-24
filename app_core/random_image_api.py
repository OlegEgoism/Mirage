from __future__ import annotations

import sys
import time
import urllib.request
from urllib.error import HTTPError
from pathlib import Path
from typing import Optional, Sequence

from .config import CACHE_DIR, RANDOM_API_URLS


class RandomImageAPI:
    def __init__(self, api_urls: Sequence[str] = RANDOM_API_URLS, target_dir: Path = CACHE_DIR) -> None:
        self.api_urls = list(api_urls)
        self.target_dir = target_dir
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def fetch_image(self) -> Optional[Path]:
        timestamp = int(time.time())
        target = self.target_dir / f"random_{timestamp}.jpg"
        for api_url in self.api_urls:
            request_url = f"{api_url}?t={timestamp}"
            request = urllib.request.Request(
                request_url,
                headers={"User-Agent": "Mozilla/5.0 (Mirage Wallpaper App)"},
            )

            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    target.write_bytes(response.read())
                return target
            except HTTPError as error:
                print(
                    f"[Mirage] Random image provider rejected request ({api_url}): {error}",
                    file=sys.stderr,
                )
            except Exception as error:
                print(f"[Mirage] Failed to fetch from provider ({api_url}): {error}", file=sys.stderr)

        print("[Mirage] Failed to fetch random image from all API providers", file=sys.stderr)
        return None
