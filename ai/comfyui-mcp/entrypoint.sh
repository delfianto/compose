#!/bin/sh
set -eu
mkdir -p "$HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME"
# The CLI restricts local discovery to loopback. Forward HTTP and WebSocket
# traffic to the generation container without modifying official tools.
socat TCP-LISTEN:8188,bind=127.0.0.1,reuseaddr,fork "TCP:${COMFY_PROXY_TARGET}" &
comfy --skip-prompt set-default /opt/ComfyUI >/dev/null
exec python /app/http-server.py
