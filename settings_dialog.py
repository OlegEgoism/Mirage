from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from config import APP_WEBSITE, SUPPORTED_EXTS
from gtk_runtime import Gtk, GdkPixbuf
from image_library import ImageLibrary
from settings_store import Settings


class SettingsDialog(Gtk.Dialog):
    def __init__(
        self,
        parent: Optional[Gtk.Window],
        settings: Settings,
        on_save: Callable[[Settings], None],
        translations: dict,
        current_wallpaper: Optional[str],
        on_next: Optional[Callable[[], None]],
    ):
        super().__init__(title=translations["settings_title"], transient_for=parent, flags=0)
        self.set_modal(True)
        self.set_default_size(360, 540)
        self.settings = settings
        self.on_save = on_save
        self.on_next = on_next
        self.T = translations

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
        self.grid.attach(self.link_box, 0, row, 2, 1)
        row += 1

        self.grid.attach(self.lbl_folder, 0, row, 1, 1)
        self.grid.attach(self.btn_folder, 1, row, 1, 1)
        row += 1

        self.grid.attach(self.lbl_interval, 0, row, 1, 1)
        self.grid.attach(self.spin_interval, 1, row, 1, 1)
        row += 1

        self.grid.attach(self.chk_shuffle, 0, row, 2, 1)
        row += 1

        self.grid.attach(self.chk_recursive, 0, row, 2, 1)
        row += 1

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.grid.attach(sep, 0, row, 2, 1)
        row += 1

        self.grid.attach(self.chk_use_selected, 0, row, 2, 1)
        row += 1

        self.grid.attach(self.btn_pick, 1, row, 1, 1)
        row += 1

        self.grid.attach(self.lbl_selected_count, 0, row, 2, 1)
        row += 1

        self.grid.attach(self.lbl_formats, 0, row, 2, 1)
        row += 1

        self.grid.attach(self.lbl_preview, 0, row, 1, 1)
        self.grid.attach(self.preview, 1, row, 1, 1)
        row += 1

        self.grid.attach(self.btn_box, 0, row, 2, 1)

        self._update_selected_label()
        self._update_formats_label()
        self._update_preview(current_wallpaper)
        self.show_all()

    def apply_language(self, translations: dict) -> None:
        self.T = translations
        self.set_title(self.T["settings_title"])
        self.link_button.set_label(self.T.get("website_label", "GitHub: Mirage"))
        self.lbl_folder.set_label(self.T["folder_label"])
        self.btn_folder.set_title(self.T["folder_label"])
        self.lbl_interval.set_label(self.T["interval_label"])
        self.chk_shuffle.set_label(self.T["shuffle"])
        self.chk_recursive.set_label(self.T["recursive"])
        self.chk_use_selected.set_label(self.T["use_selected"])
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
        exts_str = ImageLibrary.format_exts_for_label(SUPPORTED_EXTS)
        self.lbl_formats.set_text(f"{title}: {exts_str}")

    def _update_preview(self, path: Optional[str]) -> None:
        if path and Path(path).is_file():
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    path,
                    width=220,
                    height=130,
                    preserve_aspect_ratio=True,
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

        exts_str = ImageLibrary.format_exts_for_label(SUPPORTED_EXTS)
        flt = Gtk.FileFilter()
        flt.set_name(f"{self.T.get('images_filter_title', 'Images')} ({exts_str})")
        for pattern in ImageLibrary.gtk_patterns_for_exts(SUPPORTED_EXTS):
            flt.add_pattern(pattern)
        dialog.add_filter(flt)

        flt_all = Gtk.FileFilter()
        flt_all.set_name(self.T.get("filter_all", "All files"))
        flt_all.add_pattern("*")
        dialog.add_filter(flt_all)

        if dialog.run() == Gtk.ResponseType.OK:
            files = [path for path in dialog.get_filenames() if Path(path).suffix.lower() in SUPPORTED_EXTS]
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

        self.settings.save()
        self.on_save(self.settings)
        self.response(Gtk.ResponseType.OK)
