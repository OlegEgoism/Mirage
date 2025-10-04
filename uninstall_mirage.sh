#!/bin/bash

set -euo pipefail

PACKAGE_NAME="Mirage"
ENTRY_BASENAME="app"
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
      sed -n '1,40p' "$0"
      exit 0
      ;;
    *)
      echo "Неизвестный аргумент: $arg"
      exit 1
      ;;
  esac
done

# --- помощники ---
log() { echo -e "$@"; }
ask_yn() {
  $ASSUME_YES && return 0
  read -r -p "$1 [y/N]: " ans
  [[ "${ans,,}" == "y" || "${ans,,}" == "yes" ]]
}

safe_remove() {
  local path="$1"
  local desc="$2"
  if [[ -e "$path" ]]; then
    if $DRY_RUN; then
      log "🔍 DRY-RUN: будет удалён $desc: $path"
    else
      rm -rf --one-file-system "$path"
      log "✅ Удалён $desc: $path"
    fi
  else
    log "ℹ️  Не найден $desc: $path"
  fi
}

# --- пути как в build_nuitka.sh ---
APP_MENU_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"
STANDALONE_DIR="$PWD/${PACKAGE_NAME}-standalone"
RUNNER_FILE="$PWD/${PACKAGE_NAME}-run"
ONEFILE_BIN="$PWD/${PACKAGE_NAME}-onefile"

DESKTOP_MAIN="${APP_MENU_DIR}/${PACKAGE_NAME}.desktop"
# Возможные устаревшие ярлыки (на случай старых сборок)
LEGACY_ONE_AUTOSTART="${AUTOSTART_DIR}/${PACKAGE_NAME}-onefile.desktop"
LEGACY_AUTOSTART="${AUTOSTART_DIR}/${PACKAGE_NAME}.desktop"

# Конфиг и кэш
CONFIG_DIR="$HOME/.config/mirage"

# Папки сборки (если запускали build_nuitka.sh в этом каталоге)
BUILD_DIR_STANDALONE="$PWD/build_standalone"
BUILD_DIR1="$PWD/${PACKAGE_NAME}.build"
BUILD_DIR2="$PWD/${PACKAGE_NAME}.dist"
BUILD_DIR3="$PWD/${PACKAGE_NAME}.onefile-build"

echo "🗑️  Подготовка к удалению ${PACKAGE_NAME}…"
echo "    DRY_RUN = $DRY_RUN"
echo "    PURGE   = $PURGE"
echo "    ALL     = $ALL"

if ! ask_yn "Продолжить удаление ${PACKAGE_NAME}?"; then
  echo "Отменено."
  exit 0
fi

echo ""
echo "🔧 Удаление файлов приложения…"
safe_remove "$STANDALONE_DIR"  "Standalone-директория"
safe_remove "$RUNNER_FILE"     "runner-скрипт"
safe_remove "$ONEFILE_BIN"     "onefile-бинарник"

echo ""
echo "🧹 Удаление ярлыков .desktop…"
safe_remove "$DESKTOP_MAIN"        "ярлык меню"
# Удаляем автозапуски, если остались от старых версий/ручных включений
safe_remove "$LEGACY_ONE_AUTOSTART" "автозапуск (legacy onefile)"
safe_remove "$LEGACY_AUTOSTART"     "автозапуск (legacy)"

# На случай, если приложение само создавало автозапуск стандартным именем
DEFAULT_AUTOSTART="${AUTOSTART_DIR}/${PACKAGE_NAME}.desktop"
if [[ "$DEFAULT_AUTOSTART" != "$LEGACY_AUTOSTART" ]]; then
  safe_remove "$DEFAULT_AUTOSTART" "автозапуск (по умолчанию)"
fi

echo ""
if $PURGE; then
  echo "🧨 Полная очистка (purge): пользовательские настройки…"
  safe_remove "$CONFIG_DIR" "каталог настроек"
else
  echo "⚠️  Настройки в ${CONFIG_DIR} оставлены (используйте --purge для удаления)."
fi

if $ALL; then
  echo ""
  echo "🧼 Очистка временных папок сборки (--all)…"
  safe_remove "$BUILD_DIR_STANDALONE" "build_standalone"
  safe_remove "$BUILD_DIR1"           "${PACKAGE_NAME}.build"
  safe_remove "$BUILD_DIR2"           "${PACKAGE_NAME}.dist"
  safe_remove "$BUILD_DIR3"           "${PACKAGE_NAME}.onefile-build"
fi

echo ""
if $DRY_RUN; then
  echo "✅ DRY-RUN завершён. Ничего не удалено."
else
  echo "🎉 Готово. ${PACKAGE_NAME} удалён."
fi
