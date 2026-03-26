#!/bin/bash
set -e

VENV_DIR="/app/.venv"

# Check if the virtual environment exists, if not create it
if [[ ! -f "$VENV_DIR/bin/python3" ]]; then
  echo "Creating virtual environment in $VENV_DIR..."
  uv venv --seed --python 3.13 "$VENV_DIR"

  echo "Installing requirements..."
  uv pip install --no-cache -r requirements.txt
else
  echo "Virtual environment already exists in $VENV_DIR. Skipping creation."
fi

# Launch Forge
echo "Starting Forge Classic..."
exec "$VENV_DIR/bin/python3" launch.py "$@"
