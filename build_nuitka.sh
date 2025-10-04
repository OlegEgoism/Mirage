#!/bin/bash

# Nuitka build for Mirage (resources + single desktop entry)
# Проектная структура:
#   app.py
#   language.py
#   logo_app.png
#   requirements.txt
#   build_nuitka.sh  (этот файл)

set -e

PACKAGE_NAME="Mirage"
VERSION="1.1.0"          # при необходимости синхронизируй с APP_VERSION в app.py
ENTRYPOINT="app.py"      # главный файл в твоём проекте
ENTRY_BASENAME="app"     # имя бинаря, который создаёт Nuitka из app.py

echo "🔥 Building ${PACKAGE_NAME} (Nuitka)…"

# ---------- Проверка зависимостей ----------
echo "🔧 Checking system dependencies…"
if ! command -v patchelf &> /dev/null; then
  echo "Installing patchelf (required by Nuitka)…"
  sudo apt update && sudo apt install -y patchelf
fi
if ! command -v gcc &> /dev/null; then
  echo "Installing build-essential…"
  sudo apt install -y build-essential
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" &> /dev/null; then
  echo "❌ $PYTHON_BIN is not installed."
  exit 1
fi
if ! "$PYTHON_BIN" -m pip --version &> /dev/null; then
  echo "Installing python3-pip…"
  sudo apt install -y python3-pip
fi

# Внутри venv установим зависимости проекта и Nuitka
echo "📦 Installing Python deps…"
"$PYTHON_BIN" -m pip install --upgrade pip
if [[ -f "requirements.txt" ]]; then
  "$PYTHON_BIN" -m pip install -r requirements.txt
fi
if ! command -v nuitka3 &> /dev/null && ! command -v nuitka &> /dev/null; then
  "$PYTHON_BIN" -m pip install nuitka
fi

# ---------- Определяем Nuitka ----------
NUITKA_CMD="nuitka"
if command -v nuitka3 &> /dev/null; then
  NUITKA_CMD="nuitka3"
elif command -v nuitka &> /dev/null; then
  NUITKA_CMD="nuitka"
else
  echo "❌ Nuitka is not available. Try: $PYTHON_BIN -m pip install nuitka"
  exit 1
fi
echo "Using Nuitka command: $NUITKA_CMD"

# ---------- Пути меню (без автозапуска!) ----------
APP_MENU_DIR="$HOME/.local/share/applications"
mkdir -p "$APP_MENU_DIR"

DESKTOP_MAIN="${APP_MENU_DIR}/${PACKAGE_NAME}.desktop"

# ---------- Очистка предыдущих сборок ----------
rm -rf "${PACKAGE_NAME}.dist" "${PACKAGE_NAME}.build" "${PACKAGE_NAME}.onefile-build" \
       "build_standalone" "${PACKAGE_NAME}-standalone"
rm -f  "${PACKAGE_NAME}" "${PACKAGE_NAME}.bin" "${PACKAGE_NAME}-compiled" \
       "${PACKAGE_NAME}-onefile" "${PACKAGE_NAME}-run"

# ---------- Утилита записи .desktop (только меню) ----------
write_desktop_file_menu() {
  local path="$1"       # полный путь к .desktop
  local name="$2"       # Name=
  local exec_cmd="$3"   # Exec=
  local icon_path="$4"  # Icon=

  {
    echo "[Desktop Entry]"
    echo "Type=Application"
    echo "Name=${name}"
    echo "Comment=Mirage — automatic wallpaper changer (tray)"
    echo "Exec=${exec_cmd}"
    if [[ -n "$icon_path" && -f "$icon_path" ]]; then
      echo "Icon=${icon_path}"
    fi
    echo "Terminal=false"
    echo "Categories=Utility;"
    echo "TryExec=${exec_cmd%% *}"
  } > "$path"
  chmod +x "$path"
  echo "📝 Wrote desktop file (menu only): $path"
}

# ---------- Standalone ----------
echo "🚀 Compiling (standalone)…"
"$NUITKA_CMD" --standalone \
  --enable-plugin=gi \
  --include-data-files=logo_app.png=logo_app.png \
  --include-data-files=language.py=language.py \
  --assume-yes-for-downloads \
  --output-dir=build_standalone \
  --follow-imports \
  --python-flag=no_site \
  --python-flag=-O \
  "$ENTRYPOINT"

if [[ -d "build_standalone/${ENTRY_BASENAME}.dist" ]]; then
  echo "✅ Standalone build OK"
  cp -r "build_standalone/${ENTRY_BASENAME}.dist" "${PACKAGE_NAME}-standalone"

  # Runner для простого запуска из распакованной папки
  cat > "${PACKAGE_NAME}-run" <<'EOF'
#!/bin/bash
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR/Mirage-standalone"
exec ./app "$@"
EOF
  chmod +x "${PACKAGE_NAME}-run"

  STANDALONE_SIZE=$(du -sh "${PACKAGE_NAME}-standalone" | cut -f1)
  echo "📦 Standalone dir: ${PACKAGE_NAME}-standalone (size: ${STANDALONE_SIZE})"
  echo "▶️  Run: ./$(basename "${PACKAGE_NAME}-run")"
else
  echo "❌ Standalone compilation failed."
  exit 1
fi

# ---------- Onefile (опционально) ----------
echo ""
echo "🗜️ Compiling (onefile, experimental)…"
set +e
"$NUITKA_CMD" --onefile \
  --enable-plugin=gi \
  --include-data-files=logo_app.png=logo_app.png \
  --include-data-files=language.py=language.py \
  --assume-yes-for-downloads \
  --output-filename="${PACKAGE_NAME}-onefile" \
  --follow-imports \
  --python-flag=no_site \
  --python-flag=-O \
  "$ENTRYPOINT"
ONEFILE_RC=$?
set -e

if [[ $ONEFILE_RC -eq 0 && -f "${PACKAGE_NAME}-onefile" ]]; then
  chmod +x "${PACKAGE_NAME}-onefile"
  ONEFILE_SIZE=$(du -h "${PACKAGE_NAME}-onefile" | cut -f1)
  echo "✅ Onefile build OK (size: ${ONEFILE_SIZE})"
  echo "▶️  Run: ./$(basename "${PACKAGE_NAME}-onefile")"
else
  echo "⚠️ Onefile build failed or skipped; standalone is ready."
fi

# ---------- .desktop (только меню; автозапуском управляет приложение) ----------
ABS_ONEFILE_PATH="$(pwd)/${PACKAGE_NAME}-onefile"
ABS_RUNNER_PATH="$(pwd)/${PACKAGE_NAME}-run"

if [[ -f "$ABS_ONEFILE_PATH" ]]; then
  FINAL_EXEC="$ABS_ONEFILE_PATH"
  echo "🧭 Launcher target: onefile"
else
  FINAL_EXEC="$ABS_RUNNER_PATH"
  echo "🧭 Launcher target: standalone runner"
fi

ICON_CANDIDATE1="$(pwd)/${PACKAGE_NAME}-standalone/logo_app.png"
ICON_CANDIDATE2="$(pwd)/logo_app.png"
if [[ -f "$ICON_CANDIDATE1" ]]; then
  FINAL_ICON="$ICON_CANDIDATE1"
elif [[ -f "$ICON_CANDIDATE2" ]]; then
  FINAL_ICON="$ICON_CANDIDATE2"
else
  FINAL_ICON=""
fi

# Удаляем возможные устаревшие автозапуск-ярлыки из прошлых сборок
LEGACY_ONE_AUTOSTART="$HOME/.config/autostart/${PACKAGE_NAME}-onefile.desktop"
LEGACY_AUTOSTART="$HOME/.config/autostart/${PACKAGE_NAME}.desktop"
rm -f "$LEGACY_ONE_AUTOSTART" "$LEGACY_AUTOSTART"

# Создаём только .desktop для меню
write_desktop_file_menu "$DESKTOP_MAIN" "${PACKAGE_NAME}" "$FINAL_EXEC" "$FINAL_ICON"

# ---------- Финал ----------
rm -rf build_standalone

echo ""
echo "🎉 Done!"
echo "• Standalone: ${PACKAGE_NAME}-standalone/ + ${PACKAGE_NAME}-run"
echo "• Onefile  : ${PACKAGE_NAME}-onefile (если собрался)"
echo "• Menu     : ${DESKTOP_MAIN}"
echo "• Autostart: управляется из настроек приложения (чекбокс)"
echo "• Icon     : $( [[ -n "$FINAL_ICON" ]] && echo "$FINAL_ICON" || echo 'нет' )"
echo ""
echo "📦 Pack for distribution:"
echo "  tar -czf ${PACKAGE_NAME}-standalone.tar.gz ${PACKAGE_NAME}-standalone/ ${PACKAGE_NAME}-run"
echo "  # user:"
echo "  tar -xzf ${PACKAGE_NAME}-standalone.tar.gz && ./${PACKAGE_NAME}-run"
