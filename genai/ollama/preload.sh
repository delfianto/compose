#!/bin/bash

# Load environment variables
if [[ -f .env ]]; then
  export $(grep -v '^#' .env | xargs)
fi

# Set OLLAMA_HOST for the ollama CLI to connect remotely
export OLLAMA_HOST="${SIDECAR_URL:-http://ollama-smol:11434}"
export MODEL="${MODEL_NAME:-${SIDECAR_MODEL:-hf.co/mradermacher/Human-Like-Qwen2.5-1.5B-Instruct-i1-GGUF:Q4_K_M}}"

check_health() {
  echo "Checking Ollama health at $OLLAMA_HOST..."
  if ollama list > /dev/null 2>&1; then
    echo "{\"status\": \"healthy\", \"url\": \"$OLLAMA_HOST\"}"
    return 0
  else
    echo "{\"status\": \"unhealthy\", \"url\": \"$OLLAMA_HOST\"}"
    return 1
  fi
}

run_preload() {
  echo "Waiting for Ollama at $OLLAMA_HOST..."
  until ollama list > /dev/null 2>&1; do
    sleep 2
  done

  echo "Pulling model: $MODEL..."
  ollama pull "$MODEL"

  echo "Preloading $MODEL into VRAM..."
  ollama run "$MODEL" "" > /dev/null 2>&1

  echo "{\"status\": \"ready\", \"model\": \"$MODEL\"}"
}

case "$1" in
  --check)
    check_health
    ;;
  --run)
    run_preload
    ;;
  *)
    echo "Usage: $0 {--run|--check}"
    exit 1
    ;;
esac
