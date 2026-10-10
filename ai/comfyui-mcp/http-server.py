"""Serve official Comfy MCP tools using the SDK's Streamable HTTP transport."""

from comfy_mcp.server import mcp

# Docker/systemd owns the generation process and its immutable core environment.
# Keep these operations out of the agent's tool surface in this deployment.
for name in (
    "launch_comfyui",
    "stop_comfyui",
    "restart_comfyui",
    "update_comfyui",
    "switch_comfyui_version",
    "install_node",
):
    mcp.remove_tool(name)

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9100)
