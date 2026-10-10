#!/usr/bin/env bash
# Run inside the idle ComfyUI container after building Dockerfile.dlss.
set -euo pipefail
export WINEPREFIX="${DLSS5_WINEPREFIX:-/var/cache/dlss5/wineprefix}"
export WINEARCH=win64 WINEDEBUG=-all
wine_bin="${DLSS5_WINE:-/opt/proton/files/bin/wine}"
proton_files="$(dirname "$(dirname "$wine_bin")")"
mkdir -p "$WINEPREFIX"
xvfb-run -a "$wine_bin" wineboot -u
"$(dirname "$wine_bin")/wineserver" -w
system32="$WINEPREFIX/drive_c/windows/system32"
for dll in dxgi d3d11; do
    cp "$proton_files/lib/wine/dxvk/x86_64-windows/$dll.dll" "$system32/"
done
for dll in d3d12 d3d12core; do
    cp "$proton_files/lib/wine/vkd3d-proton/x86_64-windows/$dll.dll" "$system32/"
done
for dll in nvapi64 nvofapi64; do
    cp "$proton_files/lib/wine/nvapi/x86_64-windows/$dll.dll" "$system32/"
done
printf 'Prepared DLSS Wine prefix: %s\n' "$WINEPREFIX"
