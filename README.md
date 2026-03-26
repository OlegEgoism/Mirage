# Mirage

<img src="logo_app.png" width="96" alt="Mirage logo"/>

GTK tray application for automatic wallpaper rotation on Linux.

---

## 🇷🇺 Русский

### Возможности
- Автоматическая смена обоев по таймеру.
- Источник обоев:
  - локальная папка;
  - только вручную выбранные изображения;
  - случайные изображения через API.
- Режимы: shuffle, рекурсивный обход подпапок.
- Предпросмотр текущих обоев.
- Поддерживаемые форматы: JPG, JPEG, PNG, BMP, TIFF, WEBP.
- Работа из системного трея.

### Где хранятся настройки
- `~/.config/mirage/settings.json`

### Запуск в dev-режиме
1. Установить системные GTK зависимости (Debian/Ubuntu):
```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-appindicator3-0.1 gir1.2-gio-2.0
```
2. Установить Python-зависимости:
```bash
pip install -r requirements.txt
```
3. Запуск:
```bash
python3 app.py
```

### Сборка приложения (Nuitka)
```bash
chmod +x build_nuitka.sh
./build_nuitka.sh
```
Результат:
- `Mirage-standalone/` + запуск через `./Mirage-run`
- (опционально) `Mirage-onefile`

### Сборка как Python-проект (wheel/sdist)
```bash
python3 -m pip install --upgrade build
python3 -m build
```
Локальная установка:
```bash
python3 -m pip install .
mirage
```

### Документация анализа
- Полный анализ (RU): `docs/CODE_ANALYSIS_RU.md`
- Full analysis (EN): `docs/CODE_ANALYSIS_EN.md`

---

## 🇬🇧 English

### Features
- Automatic wallpaper rotation by timer.
- Wallpaper source:
  - local folder;
  - manually selected files only;
  - random images via API.
- Modes: shuffle, recursive subfolder scanning.
- Current wallpaper preview.
- Supported formats: JPG, JPEG, PNG, BMP, TIFF, WEBP.
- Runs in system tray.

### Settings location
- `~/.config/mirage/settings.json`

### Run in development mode
1. Install system GTK dependencies (Debian/Ubuntu):
```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-appindicator3-0.1 gir1.2-gio-2.0
```
2. Install Python dependencies:
```bash
pip install -r requirements.txt
```
3. Start app:
```bash
python3 app.py
```

### Build application (Nuitka)
```bash
chmod +x build_nuitka.sh
./build_nuitka.sh
```
Artifacts:
- `Mirage-standalone/` + launcher `./Mirage-run`
- (optional) `Mirage-onefile`

### Build as Python project (wheel/sdist)
```bash
python3 -m pip install --upgrade build
python3 -m build
```
Install locally:
```bash
python3 -m pip install .
mirage
```

### Analysis docs
- Full analysis (EN): `docs/CODE_ANALYSIS_EN.md`
- Полный анализ (RU): `docs/CODE_ANALYSIS_RU.md`

---

## Uninstall
```bash
chmod +x uninstall_mirage.sh
./uninstall_mirage.sh --all --purge -y
./uninstall_mirage.sh --all --dry-run
```
