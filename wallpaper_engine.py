import sys

from gtk_runtime import Gio


class WallpaperEngine:
    def __init__(self) -> None:
        try:
            self._settings = Gio.Settings.new("org.gnome.desktop.background")
        except Exception as error:
            print(f"[Mirage] Cannot access GNOME background settings: {error}", file=sys.stderr)
            self._settings = None

    def set_wallpaper(self, path: str) -> None:
        if not self._settings:
            print("[Mirage] Wallpaper engine unavailable", file=sys.stderr)
            return

        uri = f"file://{path}"
        try:
            self._settings.set_string("picture-uri", uri)
            self._settings.set_string("picture-uri-dark", uri)
        except Exception as error:
            print(f"[Mirage] Failed to set wallpaper: {error}", file=sys.stderr)
