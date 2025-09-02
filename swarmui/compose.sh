#!/usr/bin/env bash

set -e

create_user() {
  groupadd -g "$GID" srwarmui &&
    useradd -u "$UID" -g "$GID" -m -d $SWARMUI_ROOT/Home -s /bin/bash srwarmui
}

install_deps() {
  apt-get update && \
    apt-get install -y --no-install-recommends \
    git wget build-essential python3.11 \
    python3.11-venv python3.11-dev python3-pip \
    ffmpeg libglib2.0-0 libgl1 && \
    rm -rf /var/lib/apt/lists/*
}

srwarmui_git() {
  git clone --depth=1 --verbose https://github.com/mcmonkeyprojects/SwarmUI.git $SWARMUI_ROOT
  git config --global --add safe.directory $SWARMUI_ROOT

# Create the internal launch script
cat > "/SwarmUI/run.sh" <<EOF
#!/usr/bin/env bash
export HOME=$SWARMUI_ROOT/Home
$SWARMUI_ROOT/launch-linux.sh $@ --launch_mode none --host 0.0.0.0
EOF

  chown -R "$UID:$GID" $SWARMUI_ROOT
  chmod +x $SWARMUI_ROOT/run.sh $SWARMUI_ROOT/launch-linux.sh
}

srwarmui_bin() {
  cd $SWARMUI_ROOT
  bash ./launchtools/linux-build-logic.sh
}

case "$1" in
  "--stage1")
    srwarmui_git
    srwarmui_bin
    create_user
    ;;
  "--stage2")
    install_deps
    create_user
    ;;
  *)
    echo "Usage: $0 { --all | --user }"
    exit 1
    ;;
esac
