from __future__ import annotations

import json
import sys
import stat
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Callable

import gi

from language import LANGUAGES

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GdkPixbuf

# Попытка импорта AppIndicator (Ayatana или классический)
AppInd = None
try:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3 as AppInd
except (ValueError, ImportError):
    try:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AppInd
    except (ValueError, ImportError):
        pass  # AppInd остаётся None

gi.require_version("Gio", "2.0")
from gi.repository import Gio

# Константы приложения
APP_ID = "mirage.tray"
APP_VERSION = "1.1.0"
APP_AUTHOR = "Oleg Pustovalov"
APP_WEBSITE = "https://github.com/OlegEgoism/Mirage"

CONFIG_DIR = Path.home() / ".config" / "mirage"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "settings.json"

ICON_FILE = Path(__file__).parent / "logo_app.png"
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
AUTOSTART_FILE = AUTOSTART_DIR / "Mirage.desktop"

SUPPORTED_LANGS = ["ru", "en"]


def _format_exts_for_label(exts: set[str]) -> str:
    return ", ".join(sorted({e.lstrip(".").upper() for e in exts}))


def _gtk_patterns_for_exts(exts: set[str]) -> List[str]:
    patterns = []
    for ext in exts:
        lower = ext.lower()
        upper = ext.upper()
        patterns.append(f"*{lower}")
        if upper != lower:
            patterns.append(f"*{upper}")
    return patterns


def _current_exec_command() -> str:
    script_path = Path(__file__).resolve()
    if script_path.suffix.lower() == ".py":
        python = Path(sys.executable).resolve()
        return f'"{python}" "{script_path}"'
    return f'"{script_path}"'


def _desktop_entry(name: str, comment: str, icon_path: Optional[Path]) -> str:
    icon = str(icon_path.resolve()) if icon_path and icon_path.is_file() else "image-x-generic"
    exec_cmd = _current_exec_command()
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Version={APP_VERSION}\n"
        f"Name={name}\n"
        f"Comment={comment}\n"
        f"Exec={exec_cmd}\n"
        f"Icon={icon}\n"
        "Terminal=false\n"
        "Categories=Utility;\n"
        "X-GNOME-Autostart-enabled=true\n"
    )


class AutostartManager:
    @staticmethod
    def is_enabled() -> bool:
        return AUTOSTART_FILE.is_file()

    @staticmethod
    def enable(app_name: str, comment: str) -> None:
        try:
            content = _desktop_entry(app_name, comment, ICON_FILE)
            AUTOSTART_FILE.write_text(content, encoding="utf-8")
            AUTOSTART_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        except Exception as e:
            print(f"[Mirage] Autostart enable error: {e}", file=sys.stderr)

    @staticmethod
    def disable() -> None:
        try:
            if AUTOSTART_FILE.is_file():
                AUTOSTART_FILE.unlink()
        except Exception as e:
            print(f"[Mirage] Autostart disable error: {e}", file=sys.stderr)


@dataclass
class Settings:
    folder: str = str(Path.home() / "Pictures")
    interval_minutes: int = 5
    shuffle: bool = True
    recursive: bool = False
    use_selected_only: bool = False
    selected: List[str] = field(default_factory=list)
    language: str = "ru"
    autostart: bool = False

    @classmethod
    def load(cls) -> "Settings":
        if CONFIG_FILE.is_file():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                valid_data = {
                    k: v for k, v in data.items()
                    if k in cls.__dataclass_fields__
                }
                s = cls(**valid_data)
                s.autostart = AutostartManager.is_enabled()
                return s
            except Exception as e:
                print(f"[Mirage] Settings load error: {e}", file=sys.stderr)

        s = cls()
        s.autostart = AutostartManager.is_enabled()
        return s

    def save(self) -> None:
        try:
            CONFIG_FILE.write_text(
                json.dumps(self.__dict__, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[Mirage] Settings save error: {e}", file=sys.stderr)


class WallpaperEngine:
    def __init__(self) -> None:
        try:
            self._settings = Gio.Settings.new("org.gnome.desktop.background")
        except Exception as e:
            print(f"[Mirage] Cannot access GNOME background settings: {e}", file=sys.stderr)
            self._settings = None

    def set_wallpaper(self, path: str) -> None:
        if not self._settings:
            print("[Mirage] Wallpaper engine unavailable", file=sys.stderr)
            return
        uri = f"file://{path}"
        try:
            self._settings.set_string("picture-uri", uri)
            self._settings.set_string("picture-uri-dark", uri)
        except Exception as e:
            print(f"[Mirage] Failed to set wallpaper: {e}", file=sys.stderr)


def list_images(folder: Path, recursive: bool) -> List[Path]:
    if not folder.is_dir():
        return []
    exts = {e.lower() for e in SUPPORTED_EXTS}
    images: List[Path] = []

    iterator = folder.rglob("*") if recursive else folder.iterdir()
    for p in iterator:
        if p.is_file() and p.suffix.lower() in exts:
            images.append(p)

    return sorted(images)


class SettingsDialog(Gtk.Dialog):
    def __init__(
        self,
        parent: Optional[Gtk.Window],
        settings: Settings,
        on_save: Callable[["Settings"], None],
        T: dict,
        current_wallpaper: Optional[str],
        on_next: Optional[Callable[[], None]],
    ):
        super().__init__(title=T["settings_title"], transient_for=parent, flags=0)
        self.set_modal(True)
        self.set_default_size(360, 540)
        self.settings = settings
        self.on_save = on_save
        self.on_next = on_next
        self.T = T

        content = self.get_content_area()
        self.grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin=12)
        content.add(self.grid)

        self.link_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.link_box.set_hexpand(True)
        self.link_box.set_halign(Gtk.Align.END)
        self.link_button = Gtk.LinkButton(uri=APP_WEBSITE, label=self.T.get("website_label", "GitHub: Mirage"))
        self.link_box.pack_end(self.link_button, False, False, 0)

        self.lbl_folder = Gtk.Label(label=self.T["folder_label"], halign=Gtk.Align.START)
        self.btn_folder = Gtk.FileChooserButton(action=Gtk.FileChooserAction.SELECT_FOLDER)
        self.btn_folder.set_filename(self.settings.folder)

        adj = Gtk.Adjustment(
            value=self.settings.interval_minutes,
            lower=1,
            upper=1440,
            step_increment=1,
            page_increment=10,
        )
        self.spin_interval = Gtk.SpinButton(adjustment=adj, climb_rate=1, digits=0)
        self.lbl_interval = Gtk.Label(label=self.T["interval_label"], halign=Gtk.Align.START)

        self.chk_shuffle = Gtk.CheckButton(label=self.T["shuffle"], active=self.settings.shuffle)
        self.chk_recursive = Gtk.CheckButton(label=self.T["recursive"], active=self.settings.recursive)
        self.chk_use_selected = Gtk.CheckButton(label=self.T["use_selected"], active=self.settings.use_selected_only)
        self.chk_autostart = Gtk.CheckButton(label=self.T.get("autostart", "Autostart"), active=AutostartManager.is_enabled())

        self.lbl_selected_count = Gtk.Label(halign=Gtk.Align.START)
        self.btn_pick = Gtk.Button(label=self.T["pick_images"])
        self.btn_pick.connect("clicked", self._pick_images)

        self.lbl_formats = Gtk.Label(halign=Gtk.Align.START)
        self.lbl_formats.get_style_context().add_class("dim-label")

        self.lbl_preview = Gtk.Label(label=self.T["current_wallpaper"], halign=Gtk.Align.START)
        self.preview = Gtk.Image()
        self.preview.set_size_request(220, 130)

        self.btn_next = Gtk.Button(label=self.T["next"])
        self.btn_next.connect("clicked", lambda *_: self.on_next() if self.on_next else None)

        self.btn_save = Gtk.Button(label=self.T["btn_save"])
        self.btn_cancel = Gtk.Button(label=self.T["btn_cancel"])
        self.btn_save.connect("clicked", self._on_save)
        self.btn_cancel.connect("clicked", lambda *_: self.response(Gtk.ResponseType.CANCEL))

        self.btn_box = Gtk.Box(spacing=6, halign=Gtk.Align.START)
        self.btn_box.pack_start(self.btn_next, False, False, 0)
        self.btn_box.pack_start(self.btn_save, False, False, 0)
        self.btn_box.pack_start(self.btn_cancel, False, False, 0)

        row = 0
        self.grid.attach(self.link_box, 0, row, 2, 1); row += 1
        self.grid.attach(self.chk_autostart, 0, row, 2, 1); row += 1

        # --- Разделитель после Autostart ---
        sep1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.grid.attach(sep1, 0, row, 2, 1); row += 1

        self.grid.attach(self.lbl_folder, 0, row, 1, 1); self.grid.attach(self.btn_folder, 1, row, 1, 1); row += 1
        self.grid.attach(self.lbl_interval, 0, row, 1, 1); self.grid.attach(self.spin_interval, 1, row, 1, 1); row += 1
        self.grid.attach(self.chk_shuffle, 0, row, 2, 1); row += 1
        self.grid.attach(self.chk_recursive, 0, row, 2, 1); row += 1

        # --- Разделитель после Recursive ---
        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.grid.attach(sep2, 0, row, 2, 1); row += 1

        self.grid.attach(self.chk_use_selected, 0, row, 2, 1); row += 1
        self.grid.attach(self.btn_pick, 1, row, 1, 1); row += 1
        self.grid.attach(self.lbl_selected_count, 0, row, 2, 1); row += 1
        self.grid.attach(self.lbl_formats, 0, row, 2, 1); row += 1
        self.grid.attach(self.lbl_preview, 0, row, 1, 1); self.grid.attach(self.preview, 1, row, 1, 1); row += 1
        self.grid.attach(self.btn_box, 0, row, 2, 1)

        self._update_selected_label()
        self._update_formats_label()
        self._update_preview(current_wallpaper)
        self.show_all()

    def _apply_language(self, T: dict) -> None:
        self.T = T
        self.set_title(self.T["settings_title"])
        self.link_button.set_label(self.T.get("website_label", "GitHub: Mirage"))
        self.lbl_folder.set_label(self.T["folder_label"])
        self.btn_folder.set_title(self.T["folder_label"])
        self.lbl_interval.set_label(self.T["interval_label"])
        self.chk_shuffle.set_label(self.T["shuffle"])
        self.chk_recursive.set_label(self.T["recursive"])
        self.chk_use_selected.set_label(self.T["use_selected"])
        self.chk_autostart.set_label(self.T.get("autostart", "Autostart"))
        self.btn_pick.set_label(self.T["pick_images"])
        self.lbl_preview.set_label(self.T["current_wallpaper"])
        self.btn_next.set_label(self.T["next"])
        self.btn_save.set_label(self.T["btn_save"])
        self.btn_cancel.set_label(self.T["btn_cancel"])
        self._update_formats_label()

    def _update_selected_label(self) -> None:
        count = len(self.settings.selected)
        self.lbl_selected_count.set_text(self.T["selected_count"].format(count=count))

    def _update_formats_label(self) -> None:
        title = self.T.get("formats_label", "Formats")
        exts_str = _format_exts_for_label(SUPPORTED_EXTS)
        self.lbl_formats.set_text(f"{title}: {exts_str}")

    def _update_preview(self, path: Optional[str]) -> None:
        if path and Path(path).is_file():
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    path, width=220, height=130, preserve_aspect_ratio=True
                )
                self.preview.set_from_pixbuf(pixbuf)
            except Exception:
                self.preview.set_from_icon_name("image-x-generic", Gtk.IconSize.DIALOG)
        else:
            self.preview.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)

    def _pick_images(self, *_):
        dialog = Gtk.FileChooserDialog(
            title=self.T["pick_images"],
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.set_select_multiple(True)
        dialog.set_current_folder(self.settings.folder)

        exts_str = _format_exts_for_label(SUPPORTED_EXTS)
        flt = Gtk.FileFilter()
        flt.set_name(f"{self.T.get('images_filter_title', 'Images')} ({exts_str})")
        for patt in _gtk_patterns_for_exts(SUPPORTED_EXTS):
            flt.add_pattern(patt)
        dialog.add_filter(flt)

        flt_all = Gtk.FileFilter()
        flt_all.set_name(self.T.get("filter_all", "All files"))
        flt_all.add_pattern("*")
        dialog.add_filter(flt_all)

        if dialog.run() == Gtk.ResponseType.OK:
            files = [f for f in dialog.get_filenames() if Path(f).suffix.lower() in SUPPORTED_EXTS]
            self.settings.selected = files
            self._update_selected_label()
            if files:
                self._update_preview(files[0])
        dialog.destroy()

    def _on_save(self, *_):
        self.settings.folder = self.btn_folder.get_filename() or self.settings.folder
        self.settings.interval_minutes = int(self.spin_interval.get_value())
        self.settings.shuffle = self.chk_shuffle.get_active()
        self.settings.recursive = self.chk_recursive.get_active()
        self.settings.use_selected_only = self.chk_use_selected.get_active()
        want_autostart = self.chk_autostart.get_active()

        if want_autostart:
            AutostartManager.enable(
                app_name=self.T.get("app_name", "Mirage"),
                comment="Automatic change of desktop wallpaper.",
            )
        else:
            AutostartManager.disable()

        self.settings.save()
        self.on_save(self.settings)
        self.response(Gtk.ResponseType.OK)


class MirageApp:
    def __init__(self):
        self.settings = Settings.load()
        self.wall = WallpaperEngine()
        self.images: List[Path] = []
        self.playlist: List[Path] = []
        self.index = 0
        self.timer_id: Optional[int] = None
        self.paused = False
        self.current_wallpaper: Optional[str] = None
        self.settings_dialog: Optional[SettingsDialog] = None
        self._refresh_lang()

        icon_path = str(ICON_FILE) if ICON_FILE.is_file() else "image-x-generic"

        self.menu = self._build_menu()
        if AppInd is not None:
            self.ind = AppInd.Indicator.new(APP_ID, icon_path, AppInd.IndicatorCategory.APPLICATION_STATUS)
            self.ind.set_status(AppInd.IndicatorStatus.ACTIVE)
            self.ind.set_menu(self.menu)

        self._reload_images()
        if not self.playlist:
            GLib.idle_add(self.open_settings)
        else:
            GLib.idle_add(self._apply_current)
            self._start_timer()

    def _refresh_lang(self):
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
        self._refresh_lang()
        self.menu = self._build_menu()
        if AppInd:
            self.ind.set_menu(self.menu)
        if self.settings_dialog and self.settings_dialog.get_visible():
            self.settings_dialog._apply_language(self.T)

    def _effective_selection(self) -> List[Path]:
        if self.settings.use_selected_only and self.settings.selected:
            valid = [Path(p) for p in self.settings.selected if Path(p).is_file()]
            if valid:
                return sorted(valid)
        return list_images(Path(self.settings.folder), self.settings.recursive)

    def _reload_images(self) -> None:
        eff = self._effective_selection()
        self.playlist = eff.copy()
        if self.settings.shuffle and self.playlist:
            random.shuffle(self.playlist)
        self.index = 0

    def _apply_current(self) -> None:
        if not self.playlist:
            return
        p = self.playlist[self.index % len(self.playlist)]
        self.wall.set_wallpaper(str(p))
        self.current_wallpaper = str(p)
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

        def on_destroy(_dlg):
            self.settings_dialog = None

        self.settings_dialog = SettingsDialog(
            parent=None,
            settings=self.settings,
            on_save=self._on_settings_saved,
            T=self.T,
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


def main():
    app = MirageApp()
    Gtk.main()


if __name__ == "__main__":
    main()