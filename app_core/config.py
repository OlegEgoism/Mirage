from pathlib import Path

APP_ID = "mirage.tray"
APP_VERSION = "1.1.0"
APP_AUTHOR = "Oleg Pustovalov"
APP_WEBSITE = "https://github.com/OlegEgoism/Mirage"

CONFIG_DIR = Path.home() / ".config" / "mirage"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "settings.json"
CACHE_DIR = Path.home() / ".cache" / "mirage"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
RANDOM_API_URL = "https://picsum.photos/2560/1440"

ICON_FILE = Path(__file__).resolve().parent.parent / "logo_app.png"
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
SUPPORTED_LANGS = ["ru", "en", "cn", "de", "it", "es", "tr", "fr"]
