#!/bin/sh
OLLAMA_URL="http://ollama-smol:11434"
MODEL_NAME="hf.co/mradermacher/Human-Like-Qwen2.5-1.5B-Instruct-i1-GGUF:Q4_K_M"

echo "Waiting for Ollama at $OLLAMA_URL..."
until curl -s "$OLLAMA_URL/api/tags" > /dev/null; do
  sleep 2
done

echo "Pulling model: $MODEL_NAME..."
curl -s -X POST "$OLLAMA_URL/api/pull" -d "{\"name\": \"$MODEL_NAME\"}"

# Sending an empty request to the generate API loads the model
echo "Preloading $MODEL_NAME into VRAM..."
curl -s -X POST "$OLLAMA_URL/api/generate" -d "{\"model\": \"$MODEL_NAME\"}"

echo "Model $MODEL_NAME is loaded and ready on GPU."
