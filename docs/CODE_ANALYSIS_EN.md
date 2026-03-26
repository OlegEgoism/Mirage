# Mirage — full code analysis (EN)

## 1) Project purpose
Mirage is a GTK tray application that rotates desktop wallpapers on Linux (primarily GNOME/GSettings-oriented).

## 2) Architecture

### Entrypoints
- `app.py` and `app_core/app.py` both delegate startup to `app_core.mirage_app:main`.

### Core modules
- `app_core/mirage_app.py` — main orchestration layer:
  - settings bootstrap;
  - tray/menu lifecycle;
  - wallpaper rotation timer;
  - language switching;
  - settings dialog launch;
  - wallpaper apply flow (local files or API).
- `app_core/settings_dialog.py` — configuration dialog UI (Gtk.Dialog), preview, folder/file picker.
- `app_core/settings_store.py` — dataclass + JSON persistence (`~/.config/mirage/settings.json`).
- `app_core/wallpaper_engine.py` — `org.gnome.desktop.background` adapter via `Gio.Settings`.
- `app_core/random_image_api.py` — random image download from remote providers into cache.
- `app_core/image_library.py` — local image discovery/filtering.
- `app_core/language.py` — localization dictionary.
- `app_core/gtk_runtime.py` — GI/GTK/AppIndicator imports with Ayatana fallback.
- `app_core/config.py` — global constants and path config.

## 3) Strengths
- Good separation between UI, business logic, and persistence.
- Tray indicator fallback support (`AppIndicator3` / `AyatanaAppIndicator3`).
- Simple, understandable dataclass-based config model.
- Supports both curated local files and random API mode.
- Multilingual UI support.

## 4) Technical risks and constraints
- Hard dependency on GNOME GSettings backend; non-GNOME DEs may not apply wallpapers.
- `urllib` flow has no retry/backoff strategy.
- Error reporting is limited to stderr prints (no structured logging).
- No unit/integration tests in repository.
- `requirements.txt` appears to include dependencies not used by current source (`evdev`, `pynput`, `python-xlib`, `psutil`).

## 5) Build-related issues found
- `build_nuitka.sh` attempted to include root-level `language.py`, but translation code lives in `app_core/language.py`.
- No standard packaging metadata existed (`pyproject.toml`), making app-style installation less straightforward.

## 6) Improvements delivered in this change
- Added `pyproject.toml`:
  - declarative packaging metadata;
  - `mirage` console script entrypoint;
  - wheel/sdist build compatibility.
- Updated `build_nuitka.sh`:
  - removed stale include of non-existing root `language.py`.
- Updated `README.md`:
  - bilingual RU/EN documentation;
  - added package build/install and CLI run instructions.
- Added Russian companion analysis in `docs/CODE_ANALYSIS_RU.md`.

## 7) Recommended next steps
1. Add pytest coverage for `image_library`, `settings_store`, `random_image_api` (with network mocks).
2. Replace plain prints with structured `logging`.
3. Add desktop entry template + installation target.
4. Make random API provider list configurable by user.
5. Optionally add backend adapters for KDE Plasma/XFCE.
