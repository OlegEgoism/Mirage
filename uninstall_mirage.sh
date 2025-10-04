#!/bin/bash
# Uninstall Mirage + очистка артефактов Nuitka
# Usage:
#   ./uninstall_mirage.sh [--dry-run] [--purge] [--all] [-y|--yes]

set -euo pipefail

PACKAGE_NAME="Mirage"   # имя продукта (ярлыки/папки)
ENTRY_BASENAME="app"    # базовое имя входного файла (app.py -> app.*)

DRY_RUN=false
PURGE=false
ALL=false
ASSUME_YES=false

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --purge)   PURGE=true ;;
    --all)     ALL=true ;;
    --yes|-y)  ASSUME_YES=true ;;
    -h|--help)
      echo "Options: --dry-run  --purge  --all  -y|--yes"
      exit 0
      ;;
    *)
      echo "Неизвестный аргумент: $arg"
      exit 1
      ;;
  esac
done

log() { echo -e "$@"; }
ask_yn() { $ASSUME_YES && return 0; read -r -p "$1 [y/N]: " ans; [[ "${ans,,}" == y || "${ans,,}" == yes ]]; }
safe_remove() {
  local path="$1" desc="$2"
  if [[ -e "$path" ]]; then
    if $DRY_RUN; then log "🔍 DRY-RUN: будет удалён $desc: $path"
    else rm -rf --one-file-system "$path"; log "✅ Удалён $desc: $path"
    fi
  else log "ℹ️  Не найден $desc: $path"
  fi
}

APP_MENU_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"
CONFIG_DIR="$HOME/.config/mirage"

STANDALONE_DIR="$PWD/${PACKAGE_NAME}-standalone"
RUNNER_FILE="$PWD/${PACKAGE_NAME}-run"
ONEFILE_BIN="$PWD/${PACKAGE_NAME}-onefile"

DESKTOP_MAIN="${APP_MENU_DIR}/${PACKAGE_NAME}.desktop"
LEGACY_ONE_AUTOSTART="${AUTOSTART_DIR}/${PACKAGE_NAME}-onefile.desktop"
LEGACY_AUTOSTART="${AUTOSTART_DIR}/${PACKAGE_NAME}.desktop"
DEFAULT_AUTOSTART="${AUTOSTART_DIR}/${PACKAGE_NAME}.desktop"

BUILD_DIRS=(
  "$PWD/build_standalone"
  "$PWD/${PACKAGE_NAME}.build"
  "$PWD/${PACKAGE_NAME}.dist"
  "$PWD/${PACKAGE_NAME}.onefile-build"
  "$PWD/${ENTRY_BASENAME}.build"
  "$PWD/${ENTRY_BASENAME}.dist"
  "$PWD/${ENTRY_BASENAME}.onefile-build"
)

shopt -s nullglob
for d in "$PWD"/*.build "$PWD"/*.dist "$PWD"/*.onefile-build; do
  BUILD_DIRS+=("$d")
done
shopt -u nullglob

echo "🗑️  Подготовка к удалению ${PACKAGE_NAME}…"
echo "    DRY_RUN = $DRY_RUN"
echo "    PURGE   = $PURGE"
echo "    ALL     = $ALL"

if ! ask_yn "Продолжить удаление ${PACKAGE_NAME}?"; then
  echo "Отменено."; exit 0
fi

echo ""
echo "🔧 Удаление файлов приложения…"
safe_remove "$STANDALONE_DIR"  "Standalone-директория"
safe_remove "$RUNNER_FILE"     "runner-скрипт"
safe_remove "$ONEFILE_BIN"     "onefile-бинарник"

echo ""
echo "🧹 Удаление ярлыков .desktop…"
safe_remove "$DESKTOP_MAIN"         "ярлык меню"
safe_remove "$LEGACY_ONE_AUTOSTART" "автозапуск (legacy onefile)"
safe_remove "$LEGACY_AUTOSTART"     "автозапуск (legacy)"
if [[ "$DEFAULT_AUTOSTART" != "$LEGACY_AUTOSTART" ]]; then
  safe_remove "$DEFAULT_AUTOSTART" "автозапуск (по умолчанию)"
fi

echo ""
echo "🧼 Очистка артефактов сборки Nuitka…"
for d in "${BUILD_DIRS[@]}"; do
  safe_remove "$d" "артефакт сборки"
done

echo ""
if $PURGE; then
  echo "🧨 Полная очистка (purge): пользовательские настройки…"
  safe_remove "$CONFIG_DIR" "каталог настроек"
else
  echo "⚠️  Настройки в ${CONFIG_DIR} оставлены (используйте --purge для удаления)."
fi

echo ""
if $DRY_RUN; then
  echo "✅ DRY-RUN завершён. Ничего не удалено."
else
  echo "🎉 Готово. ${PACKAGE_NAME} удалён."
fi
