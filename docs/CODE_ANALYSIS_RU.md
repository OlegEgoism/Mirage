# Mirage — полный анализ кода (RU)

## 1) Назначение проекта
Mirage — GTK-приложение в системном трее для автоматической смены обоев в Linux-среде (ориентация на GNOME/GSettings).

## 2) Архитектура

### Точка входа
- `app.py` и `app_core/app.py` делегируют запуск в `app_core.mirage_app:main`.

### Основные модули
- `app_core/mirage_app.py` — главный orchestration-слой:
  - инициализация настроек;
  - создание трея и меню;
  - таймер смены обоев;
  - переключение языка;
  - открытие окна настроек;
  - применение обоев (локальные файлы или API).
- `app_core/settings_dialog.py` — UI-диалог конфигурации (Gtk.Dialog), предпросмотр, выбор папки/файлов.
- `app_core/settings_store.py` — dataclass + JSON persistence (`~/.config/mirage/settings.json`).
- `app_core/wallpaper_engine.py` — адаптер к `org.gnome.desktop.background` через `Gio.Settings`.
- `app_core/random_image_api.py` — загрузка случайных изображений из внешних API в кеш.
- `app_core/image_library.py` — поиск локальных изображений и фильтрация.
- `app_core/language.py` — словарь локализаций.
- `app_core/gtk_runtime.py` — импорты GI/GTK/AppIndicator с fallback на Ayatana.
- `app_core/config.py` — глобальные константы и пути.

## 3) Сильные стороны
- Четкое разделение ответственности между UI, бизнес-логикой и persistence.
- Наличие fallback для индикатора (`AppIndicator3` / `AyatanaAppIndicator3`).
- Простая и понятная схема конфигурации через dataclass.
- Поддержка ручного выбора файлов и API-режима.
- Многоязычность интерфейса.

## 4) Технические риски и ограничения
- Зависимость от GNOME GSettings (`org.gnome.desktop.background`) — на других DE установка может не работать.
- `urllib` без ретраев/экспоненциальной паузы может быть нестабилен на плохой сети.
- Ограниченная диагностика ошибок (print в stderr, без уровней логирования).
- Нет unit/integration тестов.
- В `requirements.txt` есть зависимости, не используемые текущим кодом (`evdev`, `pynput`, `python-xlib`, `psutil`).

## 5) Выявленные проблемы сборки
- Скрипт `build_nuitka.sh` включал `language.py` из корня, хотя файл находится в `app_core/language.py`.
- Отсутствовал стандартный packaging-конфиг (`pyproject.toml`), из-за чего проект труднее устанавливать как приложение/CLI.

## 6) Что улучшено в этом изменении
- Добавлен `pyproject.toml`:
  - декларативное описание проекта;
  - script entrypoint `mirage`;
  - совместимость со сборкой wheel/sdist.
- Обновлен `build_nuitka.sh`:
  - удалено ошибочное включение несуществующего `language.py`.
- Обновлен `README.md`:
  - добавлена двуязычная документация (RU/EN);
  - добавлены инструкции по package-сборке и CLI запуску.
- Добавлен английский mirror-анализ в `docs/CODE_ANALYSIS_EN.md`.

## 7) Рекомендации (дальше)
1. Добавить pytest для `image_library`, `settings_store`, `random_image_api` (моки сети).
2. Ввести модульный `logging` вместо `print`.
3. Добавить desktop-file шаблон и install target (`make install-desktop`).
4. Вынести API-провайдеры в пользовательскую настройку.
5. Опционально: поддержка Plasma/XFCE через отдельные backend-адаптеры.
