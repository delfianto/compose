#!/usr/bin/env bash

set -e

SWARMUI_UID=${SWARMUI_UID:-1000}
SWARMUI_GID=${SWARMUI_GID:-1000}
SWARMUI_ROOT=${SWARMUI_ROOT:-/SwarmUI}
SWARMUI_VERSION=${SWARMUI_VERSION:-latest}

create_user() {
  groupadd -f -g "$SWARMUI_GID" swarmui || true
  useradd -u "$SWARMUI_UID" -g "$SWARMUI_GID" -m -d "$SWARMUI_ROOT/Home" -s /bin/bash swarmui 2>/dev/null || true
}

install_deps() {
  apt-get update && \
    apt-get install -y --no-install-recommends \
    git wget build-essential python3.11 \
    python3.11-venv python3.11-dev python3-pip \
    ffmpeg libglib2.0-0 libgl1 && \
    rm -rf /var/lib/apt/lists/*
}

swarmui_git() {
  local tag_arg=""
  # If version is provided and isn't 'latest', clone the specific branch/tag
  if [ -n "$SWARMUI_VERSION" ] && [ "$SWARMUI_VERSION" != "latest" ]; then
    tag_arg="--branch $SWARMUI_VERSION"
  fi

  git clone --depth=1 $tag_arg --verbose https://github.com/mcmonkeyprojects/SwarmUI.git "$SWARMUI_ROOT"
  git config --global --add safe.directory "$SWARMUI_ROOT"

  # Create the internal launch script
  cat > "$SWARMUI_ROOT/run.sh" <<EOF
#!/usr/bin/env bash
export HOME=$SWARMUI_ROOT/Home
$SWARMUI_ROOT/launch-linux.sh "\$@" --launch_mode none --host 0.0.0.0
EOF

  chown -R "$SWARMUI_UID:$SWARMUI_GID" "$SWARMUI_ROOT"
  chmod +x "$SWARMUI_ROOT/run.sh" "$SWARMUI_ROOT/launch-linux.sh"
}

swarmui_bin() {
  cd "$SWARMUI_ROOT"
  bash ./launchtools/linux-build-logic.sh
}

case "$1" in
  "--stage1")
    swarmui_git
    swarmui_bin
    create_user
    ;;
  "--stage2")
    install_deps
    create_user
    cat > /usr/local/bin/entrypoint.sh << 'EOF'
#!/usr/bin/env bash

# Initialize persistent volume if it's empty
if [ ! -f "$SWARMUI_ROOT/run.sh" ]; then
    echo "Initializing persistent volume with SwarmUI source code..."
    cp -a /SwarmUI_pristine/. "$SWARMUI_ROOT/" || true
fi

# Attempt to fix ownership (will naturally fail gracefully in rootless docker)
chown -R "$SWARMUI_UID:$SWARMUI_GID" "$SWARMUI_ROOT" 2>/dev/null || true

cd "$SWARMUI_ROOT"

# Determine how to run
if [ "$(id -u)" = "0" ] && [ "$SWARMUI_UID" != "0" ]; then
    # We are root in the container, and asked to run as a different user.
    # We use setpriv, but if it fails (e.g. rootless docker limitations), we fallback to current user.
    if setpriv --reuid="$SWARMUI_UID" --regid="$SWARMUI_GID" --init-groups --clear-groups true 2>/dev/null; then
        echo "Dropping privileges to $SWARMUI_UID:$SWARMUI_GID..."
        export HOME="$SWARMUI_ROOT/Home"
        exec setpriv --reuid="$SWARMUI_UID" --regid="$SWARMUI_GID" --init-groups --clear-groups ./run.sh
    else
        echo "Notice: Running in rootless mode or lacks capabilities. Running natively."
        exec ./run.sh
    fi
else
    # We are already the right user, or requested to run as root
    exec ./run.sh
fi
EOF
    chmod +x /usr/local/bin/entrypoint.sh
    ;;
  *)
    # Fixed usage block typo
    echo "Usage: $0 { --stage1 | --stage2 }"
    exit 1
    ;;
esac
