#!/bin/bash

# Удаление Mirage из системы
# Запуск: chmod +x uninstall-mirage.sh && ./uninstall-mirage.sh

set -e  # Выход при первой ошибке

echo "🗑️ Начинаем удаление Mirage..."

# ---- Пути и кандидаты расположения артефактов ----
HOME_DIR="$HOME"
PWD_DIR="$(pwd)"

# артефакты могли быть как в $HOME, так и в текущем проекте
CANDIDATE_BASE_DIRS=("$HOME_DIR" "$PWD_DIR")

STANDALONE_DIRS=()
ONEFILE_FILES=()
RUNNERS=()

for base in "${CANDIDATE_BASE_DIRS[@]}"; do
  STANDALONE_DIRS+=("$base/Mirage-standalone")
  ONEFILE_FILES+=("$base/Mirage-onefile")
  RUNNERS+=("$base/Mirage-run")
done

# desktop-файлы
DESKTOP_MENU="$HOME_DIR/.local/share/applications/Mirage.desktop"
DESKTOP_AUTOSTART="$HOME_DIR/.config/autostart/Mirage.desktop"

# на всякий случай: возможные «устаревшие» имена
LEGACY_MENU="$HOME_DIR/.local/share/applications/Mirage-onefile.desktop"
LEGACY_AUTOSTART="$HOME_DIR/.config/autostart/Mirage-onefile.desktop"

# ---- Утилита безопасного удаления ----
safe_remove() {
    local path="$1"
    local desc="$2"
    if [[ -e "$path" ]]; then
        rm -rf "$path"
        echo "✅ Удалён $desc: $path"
    else
        echo "ℹ️  Не найден $desc: $path"
    fi
}

# ---- Проверка запущенных процессов ----
echo "🔍 Проверка запущенных процессов..."
# Ищем:
#  - бинарь onefile: Mirage-onefile
#  - standalone бинарь внутри папки: .../Mirage-standalone/app (или возможный 'Mirage')
if pgrep -f "Mirage-onefile|Mirage-standalone/.*/app|Mirage-standalone/app|Mirage-standalone/Mirage" > /dev/null; then
    echo "⚠️  Обнаружены запущенные процессы Mirage!"
    echo "   Остановите их перед удалением, примеры команд:"
    echo "   pkill -f Mirage-onefile"
    echo "   pkill -f 'Mirage-standalone/app'"
    exit 1
fi

echo "🟢 Процессов Mirage не найдено. Продолжаем…"

# ---- Удаление артефактов ----
echo ""
echo "🗑️ Удаляем компоненты…"

# standalone директории
for d in "${STANDALONE_DIRS[@]}"; do
  safe_remove "$d" "папка standalone"
done

# onefile исполняемый
for f in "${ONEFILE_FILES[@]}"; do
  safe_remove "$f" "onefile-исполняемый файл"
done

# раннеры
for r in "${RUNNERS[@]}"; do
  safe_remove "$r" "скрипт запуска (Mirage-run)"
done

# desktop entries
safe_remove "$DESKTOP_MENU"      "ярлык в меню приложений"
safe_remove "$DESKTOP_AUTOSTART" "автозапуск в системе"
safe_remove "$LEGACY_MENU"       "устаревший ярлык (onefile)"
safe_remove "$LEGACY_AUTOSTART"  "устаревший автозапуск (onefile)"

# временные каталоги сборки, если вдруг остались
safe_remove "$HOME_DIR/build_standalone" "временная папка сборки (HOME)"
safe_remove "$PWD_DIR/build_standalone"  "временная папка сборки (проект)"

echo ""
echo "🎉 Mirage полностью удалён из системы!"
echo "💡 Совет: для переустановки — запусти сборку (например, ./build_nuitka.sh)"
