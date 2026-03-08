import gi


gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GdkPixbuf

AppInd = None
try:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3 as AppInd
except (ValueError, ImportError):
    try:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AppInd
    except (ValueError, ImportError):
        pass

gi.require_version("Gio", "2.0")
from gi.repository import Gio

__all__ = ["Gtk", "GLib", "Gdk", "GdkPixbuf", "Gio", "AppInd"]
