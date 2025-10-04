from __future__ import annotations
import json
import os
import sys
import stat
import random
import subprocess
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Optional

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GdkPixbuf

AppInd = None
try:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3 as AppInd
except (ValueError, ImportError):
    try:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AppInd
    except (ValueError, ImportError):
        AppInd = None

gi.require_version("Gio", "2.0")
from gi.repository import Gio

from language import LANGUAGES, SUPPORTED_LANGS

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


def _format_exts_for_label(exts: set[str]) -> str:
    """'.jpg' -> 'JPG', join with ', '"""
    return ", ".join(sorted({e.lstrip(".").upper() for e in exts}))


def _gtk_patterns_for_exts(exts: set[str]) -> List[str]:
    """Сформировать паттерны для Gtk.FileFilter (оба регистра)."""
    pats: List[str] = []
    for e in exts:
        low = e.lower()
        up = e.upper()
        pats.append(f"*{low}")
        if up != low:
            pats.append(f"*{up}")
    return pats


def _current_exec_command() -> str:
    """
    Формирует команду Exec для .desktop:
    - если запущено как скомпилированный бинарь, используем sys.argv[0]
    - если как скрипт, используем интерпретатор + путь к app.py
    """
    argv0 = Path(sys.argv[0]).resolve()
    if argv0.suffix.lower() == ".py":
        python = Path(sys.executable).resolve()
        script = Path(__file__).resolve()
        return f'"{python}" "{script}"'
    else:
        return f'"{argv0}"'


def _desktop_entry(name: str, comment: str, icon_path: Optional[Path]) -> str:
    icon = str(icon_path.resolve()) if icon_path and icon_path.exists() else "image-x-generic"
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
        return AUTOSTART_FILE.exists()

    @staticmethod
    def enable(app_name: str, comment: str) -> None:
        try:
            content = _desktop_entry(app_name, comment, ICON_FILE)
            AUTOSTART_FILE.write_text(content, encoding="utf-8")
            AUTOSTART_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        except Exception as e:
            print(f"[Mirage] Autostart enable error: {e}")

    @staticmethod
    def disable() -> None:
        try:
            if AUTOSTART_FILE.exists():
                AUTOSTART_FILE.unlink()
        except Exception as e:
            print(f"[Mirage] Autostart disable error: {e}")


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
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                base = asdict(cls())
                base.update(data)
                s = cls(**base)
                s.autostart = AutostartManager.is_enabled()
                return s
            except Exception as e:
                print(f"[Mirage] Settings load error: {e}")
        s = cls()
        s.autostart = AutostartManager.is_enabled()
        return s

    def save(self) -> None:
        try:
            CONFIG_FILE.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[Mirage] Settings save error: {e}")


class WallpaperEngine:
    def __init__(self) -> None:
        self._settings = Gio.Settings.new("org.gnome.desktop.background")

    def set_wallpaper(self, path: str) -> None:
        uri = f"file://{path}"
        try:
            self._settings.set_string("picture-uri", uri)
            try:
                self._settings.set_string("picture-uri-dark", uri)
            except Exception:
                pass
            self._settings.apply()
        except Exception:
            try:
                subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri],
                    check=True
                )
            except Exception as e:
                print(f"[Mirage] Wallpaper error: {e}")


def list_images(folder: Path, recursive: bool) -> List[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    exts = SUPPORTED_EXTS
    images: List[Path] = []
    if recursive:
        for p in folder.rglob("*"):
            if p.is_file() and p.suffix.lower() in exts:
                images.append(p)
    else:
        for p in folder.iterdir():
            if p.is_file() and p.suffix.lower() in exts:
                images.append(p)
    images.sort()
    return images


class SettingsDialog(Gtk.Dialog):
    def __init__(self, parent: Optional[Gtk.Window], settings: Settings, on_save, T, current_wallpaper: Optional[str]):
        super().__init__(title=T["settings_title"], transient_for=parent, flags=0)
        self.set_modal(True)
        self.set_default_size(340, 520)
        self.settings = settings
        self.on_save = on_save
        self.T = T

        content = self.get_content_area()
        self.grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin=12)
        content.add(self.grid)

        self.lbl_folder = Gtk.Label()
        self.lbl_folder.set_halign(Gtk.Align.START)
        self.btn_folder = Gtk.FileChooserButton(action=Gtk.FileChooserAction.SELECT_FOLDER)
        self.btn_folder.set_hexpand(True)
        try:
            self.btn_folder.set_filename(self.settings.folder)
        except Exception:
            pass

        self.lbl_interval = Gtk.Label()
        self.lbl_interval.set_halign(Gtk.Align.START)
        adj = Gtk.Adjustment(
            value=self.settings.interval_minutes, lower=1, upper=1440, step_increment=1, page_increment=10
        )
        self.spin_interval = Gtk.SpinButton(adjustment=adj, climb_rate=1, digits=0)
        self.spin_interval.set_numeric(True)

        self.chk_shuffle = Gtk.CheckButton()
        self.chk_shuffle.set_active(self.settings.shuffle)
        self.chk_shuffle.set_halign(Gtk.Align.START)

        self.chk_recursive = Gtk.CheckButton()
        self.chk_recursive.set_active(self.settings.recursive)
        self.chk_recursive.set_halign(Gtk.Align.START)

        self.chk_use_selected = Gtk.CheckButton()
        self.chk_use_selected.set_active(self.settings.use_selected_only)
        self.chk_use_selected.set_halign(Gtk.Align.START)

        self.chk_autostart = Gtk.CheckButton()
        self.chk_autostart.set_active(AutostartManager.is_enabled())
        self.chk_autostart.set_halign(Gtk.Align.START)

        self.lbl_selected_count = Gtk.Label()
        self.lbl_selected_count.set_halign(Gtk.Align.START)

        self.btn_pick = Gtk.Button()
        self.btn_pick.connect("clicked", self._pick_images)

        self.lbl_formats = Gtk.Label()
        self.lbl_formats.set_halign(Gtk.Align.START)
        self.lbl_formats.get_style_context().add_class("dim-label")

        self.lbl_preview = Gtk.Label()
        self.lbl_preview.set_halign(Gtk.Align.START)
        self.preview = Gtk.Image()
        self.preview.set_size_request(220, 130)

        self.btn_box = Gtk.Box(spacing=6)
        self.btn_save = Gtk.Button()
        self.btn_cancel = Gtk.Button()
        self.btn_about = Gtk.Button()
        self.btn_save.connect("clicked", self._on_save)
        self.btn_cancel.connect("clicked", lambda *_: self.response(Gtk.ResponseType.CANCEL))
        self.btn_about.connect("clicked", self._show_about)
        self.btn_box.pack_start(self.btn_save, False, False, 0)
        self.btn_box.pack_start(self.btn_cancel, False, False, 0)
        self.btn_box.pack_start(self.btn_about, False, False, 0)
        self.btn_box.set_halign(Gtk.Align.START)

        row = 0
        self.grid.attach(self.chk_autostart, 0, row, 2, 1);  row += 1
        self.grid.attach(self.lbl_folder, 0, row, 1, 1);     self.grid.attach(self.btn_folder, 1, row, 1, 1); row += 1
        self.grid.attach(self.lbl_interval, 0, row, 1, 1);   self.grid.attach(self.spin_interval, 1, row, 1, 1); row += 1
        self.grid.attach(self.chk_shuffle, 0, row, 2, 1);    row += 1
        self.grid.attach(self.chk_recursive, 0, row, 2, 1);  row += 1
        self.grid.attach(self.chk_use_selected, 0, row, 2, 1); row += 1

        self.grid.attach(self.btn_pick, 1, row, 1, 1); row += 1
        self.grid.attach(self.lbl_selected_count, 0, row, 2, 1); row += 1
        self.grid.attach(self.lbl_formats, 0, row, 2, 1); row += 1
        self.grid.attach(self.lbl_preview, 0, row, 1, 1)
        self.grid.attach(self.preview, 1, row, 1, 1); row += 1
        self.grid.attach(self.btn_box, 0, row, 2, 1)

        self._apply_language(T)
        self._update_selected_label()
        self._update_formats_label()
        self._update_preview(current_wallpaper)
        self.show_all()

    def _apply_language(self, T):
        self.T = T
        self.set_title(self.T["settings_title"])
        self.lbl_folder.set_label(self.T["folder_label"])
        self.btn_folder.set_title(self.T["folder_label"])
        self.lbl_interval.set_label(self.T["interval_label"])
        self.chk_shuffle.set_label(self.T["shuffle"])
        self.chk_recursive.set_label(self.T["recursive"])
        self.chk_use_selected.set_label(self.T["use_selected"])
        self.chk_autostart.set_label(self.T.get("autostart", "Autostart"))
        self.btn_pick.set_label(self.T["pick_images"])
        self.lbl_preview.set_label(self.T["current_wallpaper"])
        self.btn_save.set_label(self.T["btn_save"])
        self.btn_cancel.set_label(self.T["btn_cancel"])
        self.btn_about.set_label(self.T["app_info"])
        self._update_formats_label()

    def _update_selected_label(self):
        self.lbl_selected_count.set_text(self.T["selected_count"].format(count=len(self.settings.selected)))

    def _update_formats_label(self):
        title = self.T.get("formats_label", "Форматы")
        exts_str = _format_exts_for_label(SUPPORTED_EXTS)
        self.lbl_formats.set_text(f"{title}: {exts_str}")

    def _update_preview(self, path: Optional[str]):
        if path and Path(path).exists():
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
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        dialog.set_select_multiple(True)
        try:
            dialog.set_current_folder(self.btn_folder.get_filename() or self.settings.folder)
        except Exception:
            pass

        exts_str = _format_exts_for_label(SUPPORTED_EXTS)
        filter_title_base = self.T.get("images_filter_title", "Изображения")
        flt = Gtk.FileFilter()
        flt.set_name(f"{filter_title_base} ({exts_str})")
        for patt in _gtk_patterns_for_exts(SUPPORTED_EXTS):
            flt.add_pattern(patt)
        dialog.add_filter(flt)

        flt_all = Gtk.FileFilter()
        flt_all.set_name(self.T.get("filter_all", "Все файлы"))
        flt_all.add_pattern("*")
        dialog.add_filter(flt_all)

        resp = dialog.run()
        if resp == Gtk.ResponseType.OK:
            files = dialog.get_filenames() or []
            valid = [f for f in files if Path(f).suffix.lower() in SUPPORTED_EXTS]
            self.settings.selected = valid
            if valid:
                self._update_preview(valid[0])
            self._update_selected_label()
        dialog.destroy()

    def _on_save(self, *_):
        self.settings.folder = self.btn_folder.get_filename() or self.settings.folder
        self.settings.interval_minutes = max(1, int(self.spin_interval.get_value()))
        self.settings.shuffle = self.chk_shuffle.get_active()
        self.settings.recursive = self.chk_recursive.get_active()
        self.settings.use_selected_only = self.chk_use_selected.get_active()
        want_autostart = self.chk_autostart.get_active()
        self.settings.autostart = want_autostart
        if want_autostart:
            AutostartManager.enable(
                app_name=self.T.get("app_name", "Mirage"),
                comment=self.T.get("about_comments", "Automatic change of desktop wallpaper.")
            )
        else:
            AutostartManager.disable()

        self.settings.save()

        if callable(self.on_save):
            self.on_save(self.settings)
        self.response(Gtk.ResponseType.OK)

    def _show_about(self, *_):
        lang_code = "en" if self.T.get("language_name") == "English" else "ru"
        locale_map = {
            "en": "en_US.UTF-8",
            "ru": "ru_RU.UTF-8",
        }
        target = locale_map.get(lang_code, "en_US.UTF-8")

        prev = {k: os.environ.get(k) for k in ("LANGUAGE", "LC_ALL", "LANG")}
        try:
            GLib.setenv("LANGUAGE", target, True)
            GLib.setenv("LC_ALL", target, True)
            GLib.setenv("LANG", target, True)

            about = Gtk.AboutDialog(transient_for=self, modal=True)
            about.set_program_name(self.T.get("app_name", "Mirage"))
            about.set_version(APP_VERSION)
            about.set_comments(self.T["about_comments"])
            about.set_website(APP_WEBSITE)
            about.set_website_label(self.T["about_website_label"])
            about.set_authors([APP_AUTHOR])
            about.set_license(self.T["about_license"])
            about.set_wrap_license(True)
            if ICON_FILE.exists():
                about.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_scale(str(ICON_FILE), 64, 64, True))
            about.run()
            about.destroy()
        finally:
            for k, v in prev.items():
                if v is None:
                    GLib.unsetenv(k)
                else:
                    GLib.setenv(k, v, True)


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

        self.icon_name = str(ICON_FILE) if ICON_FILE.exists() else "image-x-generic"

        if AppInd is None:
            print("[Mirage] AppIndicator unavailable.")
            self.menu = self._build_menu()
        else:
            self.ind = AppInd.Indicator.new(APP_ID, self.icon_name, AppInd.IndicatorCategory.APPLICATION_STATUS)
            self.ind.set_status(AppInd.IndicatorStatus.ACTIVE)
            self.menu = self._build_menu()
            self.ind.set_menu(self.menu)

        self._reload_images()
        if not self.playlist:
            GLib.idle_add(self.open_settings)
        else:
            GLib.idle_add(self._apply_current)
            self._start_timer()

    def _refresh_lang(self):
        self.T = LANGUAGES.get(self.settings.language, LANGUAGES["ru"])

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
        for lang in SUPPORTED_LANGS:
            sub = Gtk.MenuItem(label=LANGUAGES[lang]["language_name"])
            sub.connect("activate", lambda _, l=lang: self._set_language(l))
            lang_menu.append(sub)
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
            valid = [Path(p) for p in self.settings.selected if Path(p).exists()]
            if valid:
                return sorted(valid)
        return list_images(Path(self.settings.folder), self.settings.recursive)

    def _reload_images(self) -> None:
        self.images = list_images(Path(self.settings.folder), self.settings.recursive)
        eff = self._effective_selection()
        self.playlist = eff.copy()
        if not self.playlist:
            self.index = 0
            return
        if self.settings.shuffle:
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

        self.settings_dialog = SettingsDialog(
            None,
            self.settings,
            on_save=self._on_settings_saved,
            T=self.T,
            current_wallpaper=self.current_wallpaper
        )

        def _on_destroy(_dlg):
            self.settings_dialog = None

        self.settings_dialog.connect("destroy", _on_destroy)

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
