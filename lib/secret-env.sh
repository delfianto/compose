#!/bin/sh
# Export every mounted docker secret as an env var, then exec the image's
# original entrypoint (passed as the container command).
# Naming: all-lowercase secret names are uppercased (google_api_key ->
# GOOGLE_API_KEY). Names containing an uppercase letter are exported verbatim --
# use `target:` in the compose secrets block when uppercasing can't produce the
# var name (e.g. target: FORGEJO__database__PASSWD).
set -eu
for f in /run/secrets/*; do
  [ -f "$f" ] || continue
  name=$(basename "$f")
  case "$name" in
    *[A-Z]*) var=$name ;;
    *)       var=$(printf %s "$name" | tr '[:lower:]' '[:upper:]') ;;
  esac
  case "$var" in
    *[!A-Za-z0-9_]*|[0-9]*) echo "secret-env: skipping '$name'" >&2; continue ;;
  esac
  export "$var=$(cat "$f")"
done

# Perform variable substitution on existing env vars to expand secret references
for var in $(env | cut -d= -f1); do
  case "$var" in
    PATH|HOME|PWD|USER|UID|GID|SHELL|IFS|OPTIND|PS1|PS2|DROP_USER) continue ;;
  esac
  eval "val=\${$var:-}"
  case "$val" in
    *\$*)
      eval "val=\"$val\""
      export "$var=$val"
      ;;
  esac
done

# Container uid 0 maps to host uid 0 only under a real root daemon. Under
# rootless Docker (or userns-remap) it maps to an unprivileged host uid, so
# dropping to DROP_USER buys no extra isolation -- just subuid file-ownership
# friction -- and can be skipped, UNLESS the app itself refuses to run as
# uid 0 for its own reasons (e.g. Forgejo hard-exits as root); set
# FORCE_DROP_USER=1 for those.
is_real_root() {
  read -r cid hid rest < /proc/self/uid_map
  [ "$cid" = "0" ] && [ "$hid" = "0" ]
}

if [ "${DROP_USER:-}" ] && { is_real_root || [ "${FORCE_DROP_USER:-}" ]; }; then
  if command -v gosu >/dev/null 2>&1; then
    exec gosu "$DROP_USER" "$@"
  elif command -v su >/dev/null 2>&1; then
    exec su -p -s /bin/sh "$DROP_USER" -c 'exec "$@"' dummy -- "$@"
  else
    echo "secret-env: DROP_USER set to $DROP_USER but neither gosu nor su found" >&2
    exit 1
  fi
else
  if [ "${DROP_USER:-}" ]; then
    echo "secret-env: rootless docker detected, container root is unprivileged -- skipping drop to $DROP_USER" >&2
  fi
  exec "$@"
fi
