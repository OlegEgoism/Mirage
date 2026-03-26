from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from .config import APP_WEBSITE, SUPPORTED_EXTS
from .gtk_runtime import Gtk, GdkPixbuf
from .image_library import ImageLibrary
from .settings_store import Settings


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
        self.set_default_size(460, 560)
        self.settings = settings
        self.on_save = on_save
        self.on_next = on_next
        self.T = translations

        self.link_button = Gtk.LinkButton(uri=APP_WEBSITE, label=self.T.get("website_label", "GitHub: Mirage"))

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
        self.chk_api_random = Gtk.CheckButton(label=self.T["use_api_random"], active=self.settings.use_api_random)
        self.chk_api_random.connect("toggled", self._sync_source_controls)
        self.chk_use_selected = Gtk.CheckButton(label=self.T["use_selected"], active=self.settings.use_selected_only)

        self.lbl_selected_count = Gtk.Label(halign=Gtk.Align.START)
        self.btn_pick = Gtk.Button(label=self.T["pick_images"])
        self.btn_pick.connect("clicked", self._pick_images)

        self.lbl_formats = Gtk.Label(halign=Gtk.Align.START)
        self.lbl_formats.get_style_context().add_class("dim-label")

        self.lbl_preview = Gtk.Label(label=self.T["current_wallpaper"], halign=Gtk.Align.START)
        self.preview = Gtk.Image()
        self.preview.set_size_request(320, 190)

        self.btn_next = Gtk.Button(label=self.T["next"])
        self.btn_next.connect("clicked", lambda *_: self.on_next() if self.on_next else None)

        self.btn_save = Gtk.Button(label=self.T["btn_save"])
        self.btn_cancel = Gtk.Button(label=self.T["btn_cancel"])
        self.btn_save.connect("clicked", self._on_save)
        self.btn_cancel.connect("clicked", lambda *_: self.response(Gtk.ResponseType.CANCEL))

        self._build_layout()
        self._update_selected_label()
        self._update_formats_label()
        self._update_preview(current_wallpaper)
        self._sync_source_controls()
        self.show_all()

    def _build_layout(self) -> None:
        content = self.get_content_area()
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=12)
        content.add(root_box)

        link_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        link_box.set_halign(Gtk.Align.END)
        link_box.pack_end(self.link_button, False, False, 0)
        root_box.pack_start(link_box, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.set_hexpand(True)
        self.notebook.set_vexpand(True)
        root_box.pack_start(self.notebook, True, True, 0)

        tab_general = self._build_general_tab()
        tab_sources = self._build_sources_tab()
        tab_preview = self._build_preview_tab()

        self.tab_general_label = Gtk.Label(label=self.T.get("tab_general", "General"))
        self.tab_sources_label = Gtk.Label(label=self.T.get("tab_sources", "Sources"))
        self.tab_preview_label = Gtk.Label(label=self.T.get("tab_preview", "Preview"))

        self.notebook.append_page(tab_general, self.tab_general_label)
        self.notebook.append_page(tab_sources, self.tab_sources_label)
        self.notebook.append_page(tab_preview, self.tab_preview_label)

        self.btn_box = Gtk.Box(spacing=6, halign=Gtk.Align.END)
        self.btn_box.pack_start(self.btn_next, False, False, 0)
        self.btn_box.pack_start(self.btn_cancel, False, False, 0)
        self.btn_box.pack_start(self.btn_save, False, False, 0)
        root_box.pack_start(self.btn_box, False, False, 0)

    def _build_general_tab(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=10)

        folder_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        folder_box.pack_start(self.lbl_folder, False, False, 0)
        folder_box.pack_start(self.btn_folder, False, False, 0)

        interval_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        interval_box.pack_start(self.lbl_interval, False, False, 0)
        interval_box.pack_start(self.spin_interval, False, False, 0)

        box.pack_start(folder_box, False, False, 0)
        box.pack_start(interval_box, False, False, 0)
        box.pack_start(self.chk_shuffle, False, False, 0)
        box.pack_start(self.chk_recursive, False, False, 0)

        return box

    def _build_sources_tab(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=10)

        pick_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pick_box.pack_start(self.btn_pick, False, False, 0)

        box.pack_start(self.chk_api_random, False, False, 0)
        box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 4)
        box.pack_start(self.chk_use_selected, False, False, 0)
        box.pack_start(pick_box, False, False, 0)
        box.pack_start(self.lbl_selected_count, False, False, 0)
        box.pack_start(self.lbl_formats, False, False, 0)

        return box

    def _build_preview_tab(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=10)
        box.pack_start(self.lbl_preview, False, False, 0)
        box.pack_start(self.preview, True, True, 0)
        return box

    def apply_language(self, translations: dict) -> None:
        self.T = translations
        self.set_title(self.T["settings_title"])
        self.link_button.set_label(self.T.get("website_label", "GitHub: Mirage"))
        self.lbl_folder.set_label(self.T["folder_label"])
        self.btn_folder.set_title(self.T["folder_label"])
        self.lbl_interval.set_label(self.T["interval_label"])
        self.chk_shuffle.set_label(self.T["shuffle"])
        self.chk_recursive.set_label(self.T["recursive"])
        self.chk_api_random.set_label(self.T["use_api_random"])
        self.chk_use_selected.set_label(self.T["use_selected"])
        self.btn_pick.set_label(self.T["pick_images"])
        self.lbl_preview.set_label(self.T["current_wallpaper"])
        self.btn_next.set_label(self.T["next"])
        self.btn_save.set_label(self.T["btn_save"])
        self.btn_cancel.set_label(self.T["btn_cancel"])
        self.tab_general_label.set_label(self.T.get("tab_general", "General"))
        self.tab_sources_label.set_label(self.T.get("tab_sources", "Sources"))
        self.tab_preview_label.set_label(self.T.get("tab_preview", "Preview"))
        self._update_formats_label()
        self._update_selected_label()

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
                    width=320,
                    height=190,
                    preserve_aspect_ratio=True,
                )
                self.preview.set_from_pixbuf(pixbuf)
            except Exception:
                self.preview.set_from_icon_name("image-x-generic", Gtk.IconSize.DIALOG)
        else:
            self.preview.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)

    def _sync_source_controls(self, *_):
        use_api_random = self.chk_api_random.get_active()
        self.btn_folder.set_sensitive(not use_api_random)
        self.chk_recursive.set_sensitive(not use_api_random)
        self.chk_use_selected.set_sensitive(not use_api_random)
        self.btn_pick.set_sensitive(not use_api_random)

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
                self.notebook.set_current_page(2)
        dialog.destroy()

    def _on_save(self, *_):
        self.settings.folder = self.btn_folder.get_filename() or self.settings.folder
        self.settings.interval_minutes = int(self.spin_interval.get_value())
        self.settings.shuffle = self.chk_shuffle.get_active()
        self.settings.recursive = self.chk_recursive.get_active()
        self.settings.use_api_random = self.chk_api_random.get_active()
        self.settings.use_selected_only = self.chk_use_selected.get_active()

        self.settings.save()
        self.on_save(self.settings)
        self.response(Gtk.ResponseType.OK)
