#!/bin/sh
# Packs dist/PrintPicker.app into a disk image with an Applications shortcut for drag-and-drop.
#
#     uv run pyinstaller packaging/printpicker.spec --noconfirm
#     packaging/macos/make-dmg.sh out/PrintPicker-macos-arm64.dmg
set -eu

out="${1:?usage: make-dmg.sh OUTPUT.dmg}"
root="$(cd "$(dirname "$0")/../.." && pwd)"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

ditto "$root/dist/PrintPicker.app" "$stage/PrintPicker.app"
ln -s /Applications "$stage/Applications"
mkdir -p "$(dirname "$out")"

# hdiutil sometimes fails with "Resource busy" on CI machines: try a few times.
for attempt in 1 2 3 4 5; do
    if hdiutil create -volname PrintPicker -srcfolder "$stage" -fs HFS+ -format UDZO -ov "$out"; then
        exit 0
    fi
    echo "hdiutil failed (attempt $attempt), retrying..." >&2
    sleep 5
done
exit 1
