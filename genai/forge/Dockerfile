FROM nvidia/cuda:13.1.1-base-ubuntu24.04

# Install system dependencies and Python 3.13 via deadsnakes PPA
RUN apt-get update && apt-get install -y software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update \
    && apt-get install -y python3.13 python3.13-venv python3.13-dev git wget libgl1 libglib2.0-0 libglib2.0-dev libcairo2-dev gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Install 'uv' for fast package management (required by Forge Neo)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Clone the specific active fork (shallow clone to save space) and remove .git
RUN git clone --depth 1 --branch neo https://github.com/haoming02/sd-webui-forge-classic.git . \
    && rm -rf .git

    # Copy the entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Use the entrypoint script to launch
ENTRYPOINT ["/entrypoint.sh"]
CMD ["--listen", "--port", "7860"]
