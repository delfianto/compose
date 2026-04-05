#!/bin/bash
docker buildx build --push \
  -t ghcr.io/delfianto/ik_llama_cpu_zen5:latest \
  -f Dockerfile .
