#!/bin/sh
# Adds PrintPicker to the application menu of the current user (no root needed).
# Run it from the extracted PrintPicker folder:  ./install-desktop-entry.sh
# Remove it again with:                          ./install-desktop-entry.sh --uninstall
set -eu

here="$(cd "$(dirname "$0")" && pwd)"
apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
icons="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/512x512/apps"
entry="$apps/io.github.giacomoguaresi.printpicker.desktop"

if [ "${1:-}" = "--uninstall" ]; then
    rm -f "$entry" "$icons/printpicker.png"
    echo "PrintPicker removed from the application menu."
    exit 0
fi

mkdir -p "$apps" "$icons"
cp "$here/printpicker.png" "$icons/printpicker.png"
sed "s|@EXEC@|$here/PrintPicker|" "$here/printpicker.desktop" > "$entry"
chmod +x "$entry"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$apps" || true
echo "PrintPicker added to the application menu."
