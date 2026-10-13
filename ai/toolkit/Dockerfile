FROM ostris/aitoolkit:latest

# Keep MCP dependencies separate from Torch, Diffusers and the training environment.
COPY mcp_adapter/requirements.txt /tmp/toolkit-mcp-requirements.txt
RUN python -m venv /opt/toolkit-mcp \
    && /opt/toolkit-mcp/bin/pip install --no-cache-dir -r /tmp/toolkit-mcp-requirements.txt

# SQLite's WAL/SHM files must persist together with the DB. Keep upstream paths.
RUN mkdir -p /app/ai-toolkit/state \
    && rm -f /app/ai-toolkit/aitk_db.db \
    && ln -s state/aitk_db.db /app/ai-toolkit/aitk_db.db
