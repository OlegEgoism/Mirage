from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .config import CONFIG_FILE


@dataclass
class Settings:
    folder: str = str(Path.home() / "Pictures")
    interval_minutes: int = 5
    shuffle: bool = True
    recursive: bool = False
    use_selected_only: bool = False
    use_api_random: bool = False
    selected: List[str] = field(default_factory=list)
    language: str = "ru"

    @classmethod
    def load(cls) -> "Settings":
        if CONFIG_FILE.is_file():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                valid_data = {
                    key: value for key, value in data.items()
                    if key in cls.__dataclass_fields__
                }
                return cls(**valid_data)
            except Exception as error:
                print(f"[Mirage] Settings load error: {error}", file=sys.stderr)
        return cls()

    def save(self) -> None:
        try:
            CONFIG_FILE.write_text(
                json.dumps(self.__dict__, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as error:
            print(f"[Mirage] Settings save error: {error}", file=sys.stderr)
