#!/bin/sh
# Packs dist/PrintPicker/ into a single-file AppImage.
#
#     uv run pyinstaller packaging/printpicker.spec --noconfirm
#     packaging/linux/make-appimage.sh out/PrintPicker-linux-x86_64.AppImage
#
# Downloads appimagetool on first use (into build/), so it needs a network connection.
set -eu

out="${1:?usage: make-appimage.sh OUTPUT.AppImage}"
root="$(cd "$(dirname "$0")/../.." && pwd)"
tool="$root/build/appimagetool-x86_64.AppImage"
appdir="$root/build/PrintPicker.AppDir"
entry="io.github.giacomoguaresi.printpicker.desktop"

if [ ! -x "$tool" ]; then
    mkdir -p "$(dirname "$tool")"
    curl -fsSL -o "$tool" \
        https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x "$tool"
fi

rm -rf "$appdir"
mkdir -p "$appdir/usr/lib"
cp -a "$root/dist/PrintPicker" "$appdir/usr/lib/PrintPicker"
cp "$root/packaging/icons/printpicker.png" "$appdir/printpicker.png"
ln -s printpicker.png "$appdir/.DirIcon"
sed "s|@EXEC@|PrintPicker|" "$root/packaging/linux/printpicker.desktop" > "$appdir/$entry"
cat > "$appdir/AppRun" <<'EOF'
#!/bin/sh
here="$(dirname "$(readlink -f "$0")")"
exec "$here/usr/lib/PrintPicker/PrintPicker" "$@"
EOF
chmod +x "$appdir/AppRun"

mkdir -p "$(dirname "$out")"
# Extract-and-run: CI machines have no FUSE to mount appimagetool itself.
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$tool" --no-appstream "$appdir" "$out"
