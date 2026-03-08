from __future__ import annotations

import random
from pathlib import Path
from typing import List, Optional

from config import APP_ID, ICON_FILE, SUPPORTED_LANGS
from gtk_runtime import AppInd, GLib, Gtk
from image_library import ImageLibrary
from language import LANGUAGES
from settings_dialog import SettingsDialog
from settings_store import Settings
from wallpaper_engine import WallpaperEngine


class MirageApp:
    def __init__(self):
        self.settings = Settings.load()
        self.wallpaper_engine = WallpaperEngine()
        self.playlist: List[Path] = []
        self.index = 0
        self.timer_id: Optional[int] = None
        self.paused = False
        self.current_wallpaper: Optional[str] = None
        self.settings_dialog: Optional[SettingsDialog] = None
        self._refresh_language()

        icon_path = str(ICON_FILE) if ICON_FILE.is_file() else "image-x-generic"

        self.menu = self._build_menu()
        if AppInd is not None:
            self.indicator = AppInd.Indicator.new(APP_ID, icon_path, AppInd.IndicatorCategory.APPLICATION_STATUS)
            self.indicator.set_status(AppInd.IndicatorStatus.ACTIVE)
            self.indicator.set_menu(self.menu)

        self._reload_images()
        if not self.playlist:
            GLib.idle_add(self.open_settings)
        else:
            GLib.idle_add(self._apply_current)
            self._start_timer()

    def _refresh_language(self):
        self.T = LANGUAGES.get(self.settings.language, LANGUAGES["ru"])

    def _on_lang_toggled(self, menu_item: Gtk.RadioMenuItem, lang: str):
        if menu_item.get_active() and lang != self.settings.language:
            self._set_language(lang)

    def _build_menu(self) -> Gtk.Menu:
        menu = Gtk.Menu()

        self.item_pause = Gtk.MenuItem(label=self.T["pause"])
        self.item_pause.connect("activate", self._toggle_pause)
        menu.append(self.item_pause)

        item_next = Gtk.MenuItem(label=self.T["next"])
        item_next.connect("activate", lambda *_: self.next_wallpaper())
        menu.append(item_next)

        menu.append(Gtk.SeparatorMenuItem())

        lang_item = Gtk.MenuItem(label=self.T["menu_language"])
        lang_menu = Gtk.Menu()
        group = None
        for lang in SUPPORTED_LANGS:
            label = LANGUAGES[lang]["language_name"]
            radio = Gtk.RadioMenuItem.new_with_label(group, label)
            if group is None:
                group = radio.get_group()
            radio.set_active(lang == self.settings.language)
            radio.connect("toggled", self._on_lang_toggled, lang)
            lang_menu.append(radio)
        lang_item.set_submenu(lang_menu)
        menu.append(lang_item)

        item_settings = Gtk.MenuItem(label=self.T["settings"])
        item_settings.connect("activate", lambda *_: self.open_settings())
        menu.append(item_settings)

        menu.append(Gtk.SeparatorMenuItem())

        item_quit = Gtk.MenuItem(label=self.T["quit"])
        item_quit.connect("activate", self.quit)
        menu.append(item_quit)

        menu.show_all()
        return menu

    def _set_language(self, lang: str):
        if lang not in SUPPORTED_LANGS:
            return

        self.settings.language = lang
        self.settings.save()
        self._refresh_language()
        self.menu = self._build_menu()
        if AppInd:
            self.indicator.set_menu(self.menu)
        if self.settings_dialog and self.settings_dialog.get_visible():
            self.settings_dialog.apply_language(self.T)

    def _reload_images(self) -> None:
        self.playlist = ImageLibrary.effective_selection(self.settings)
        if self.settings.shuffle and self.playlist:
            random.shuffle(self.playlist)
        self.index = 0

    def _apply_current(self) -> None:
        if not self.playlist:
            return

        current_path = self.playlist[self.index % len(self.playlist)]
        self.wallpaper_engine.set_wallpaper(str(current_path))
        self.current_wallpaper = str(current_path)
        if self.settings_dialog:
            self.settings_dialog._update_preview(self.current_wallpaper)

    def next_wallpaper(self) -> None:
        if not self.playlist:
            return

        self.index = (self.index + 1) % len(self.playlist)
        self._apply_current()

    def _tick(self) -> bool:
        if not self.paused:
            self.next_wallpaper()
        return True

    def _start_timer(self) -> None:
        self._stop_timer()
        seconds = max(60, self.settings.interval_minutes * 60)
        self.timer_id = GLib.timeout_add_seconds(seconds, self._tick)

    def _stop_timer(self) -> None:
        if self.timer_id is not None:
            GLib.source_remove(self.timer_id)
            self.timer_id = None

    def _toggle_pause(self, *_):
        self.paused = not self.paused
        self.item_pause.set_label(self.T["resume"] if self.paused else self.T["pause"])

    def open_settings(self, *_):
        if self.settings_dialog and self.settings_dialog.get_visible():
            self.settings_dialog.present()
            return

        def on_destroy(_dialog):
            self.settings_dialog = None

        self.settings_dialog = SettingsDialog(
            parent=None,
            settings=self.settings,
            on_save=self._on_settings_saved,
            translations=self.T,
            current_wallpaper=self.current_wallpaper,
            on_next=self.next_wallpaper,
        )
        self.settings_dialog.connect("destroy", on_destroy)
        self.settings_dialog.run()
        self.settings_dialog.destroy()

    def _on_settings_saved(self, _settings: Settings):
        self._reload_images()
        self._apply_current()
        self._start_timer()

    def quit(self, *_):
        self._stop_timer()
        Gtk.main_quit()


def main() -> None:
    MirageApp()
    Gtk.main()
