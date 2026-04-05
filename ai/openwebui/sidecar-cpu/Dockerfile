# Stage 1: Build with GCC 14 (Zen 5 Support)
FROM gcc:14 AS builder
RUN apt-get update && apt-get install -y cmake ninja-build libcurl4-openssl-dev git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN git clone --recursive https://github.com/ikawrakow/ik_llama.cpp.git .

# Zen 5 Optimized Build
RUN mkdir build && cd build && \
    cmake .. -GNinja -DGGML_CUDA=OFF \
    -DCMAKE_C_FLAGS="-march=znver5 -O3 -pipe -flto" \
    -DCMAKE_CXX_FLAGS="-march=znver5 -O3 -pipe -flto" \
    -DGGML_AVX512=ON -DGGML_AVX512_VBMI=ON -DGGML_AVX512_VNNI=ON -DGGML_OPENMP=ON
RUN cmake --build build --config Release --target llama-server

# --- NEW: Gather libraries in the builder stage ---
RUN mkdir -p /app/dist/libs && \
    cp build/bin/llama-server /app/dist/ && \
    find build -name "*.so*" -exec cp -vP {} /app/dist/libs/ \;

# Stage 2: Runtime
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y libcurl4 libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Copy from the staging area we created
COPY --from=builder /app/dist/llama-server /app/bin/llama-server
COPY --from=builder /app/dist/libs/* /usr/lib/

# Refresh library cache
RUN ldconfig

EXPOSE 8080
ENTRYPOINT ["/app/bin/llama-server"]
