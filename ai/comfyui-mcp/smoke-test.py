"""Exercise the official HTTP sidecar against this host's known SDXL workflow."""

import asyncio
import json
import os
import time
import urllib.request
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ROOT = Path("/data/user/default/workflow-backups/official-mcp-sidecar-test")
CORE = os.environ["COMFY_LOCAL_URL"].rstrip("/")


def queue():
    with urllib.request.urlopen(CORE + "/queue", timeout=10) as response:
        return json.load(response)


async def main():
    state = queue()
    if state["queue_running"] or state["queue_pending"]:
        raise RuntimeError("Generation queue is busy; retry when idle.")
    ROOT.mkdir(parents=True, exist_ok=True)
    source = Path("/data/user/default/workflow-backups/official-mcp-test/workflow.json")
    workflow = json.loads(source.read_text())
    workflow["9"]["inputs"]["filename_prefix"] = "official-mcp-sidecar-test/distorch"
    path = ROOT / "workflow.json"
    path.write_text(json.dumps(workflow, indent=2))
    summary = {}
    async with (
        streamable_http_client("http://127.0.0.1:9100/mcp") as (read, write),
        ClientSession(read, write) as session,
    ):
        init = await session.initialize()
        summary["server"] = init.server_info.model_dump()
        tools = await session.list_tools()
        summary["tools"] = [tool.name for tool in tools.tools]
        assert "clear_vram" not in summary["tools"]
        assert "free_memory" in summary["tools"]

        async def call(name, args, label=None):
            start = time.monotonic()
            result = await asyncio.wait_for(session.call_tool(name, args), 150)
            label = label or name
            (ROOT / (label + ".json")).write_text(result.model_dump_json(indent=2))
            text = next(c.text for c in result.content if c.type == "text")
            if result.is_error:
                raise RuntimeError(name + ": " + text)
            data = json.loads(text)
            summary[label] = {"seconds": round(time.monotonic() - start, 2)}
            print(label, "passed", flush=True)
            return data

        info = await call("server_info", {})
        assert info["server"]["running"]
        nodes = await call(
            "nodes",
            {
                "action": "search",
                "query": "CheckpointLoaderAdvancedDisTorch2MultiGPU",
            },
        )
        assert nodes["count"] >= 1
        models = await call(
            "search_models", {"query": "intorealism", "folder": "checkpoints"}
        )
        assert models["total"] >= 1
        valid = await call("validate_workflow", {"workflow_path": str(path)})
        assert valid["valid"]
        await call("system_stats", {}, "stats-before")
        try:
            result = await call(
                "run_workflow",
                {"workflow_path": str(path), "wait": True, "timeout_seconds": 110},
            )
            assert result["status"] == "completed"
            prompt_id = result["prompt_id"]
            summary["prompt_id"] = prompt_id
            status = await call("job", {"action": "status", "prompt_id": prompt_id})
            assert status["status"] == "completed"
            outputs = await call(
                "fetch_outputs",
                {"prompt_id": prompt_id, "out_dir": str(ROOT / "retrieved")},
            )
            assert outputs["files"]
            for output in outputs["files"]:
                image = Path(output["path"])
                assert image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
            loaded = await call("system_stats", {}, "stats-loaded")
        finally:
            state = queue()
            if not state["queue_running"] and not state["queue_pending"]:
                await call("free_memory", {"unload_models": True, "free_memory": True})
        await asyncio.sleep(4)
        freed = await call("system_stats", {}, "stats-freed")
        summary["gpu_reclaimed_gib"] = {
            before["name"]: round(
                (after["vram_free"] - before["vram_free"]) / 1024**3, 2
            )
            for before, after in zip(loaded["devices"], freed["devices"])
        }
    (ROOT / "report.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
