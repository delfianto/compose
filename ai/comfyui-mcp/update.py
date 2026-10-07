#!/usr/bin/env python3
"""Build the latest stable MCP release and restart only its systemd service."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request


def run(*args, capture=False):
    return subprocess.run(args, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "compose-comfyui-mcp-updater"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-only", action="store_true", help="build without restarting")
    parser.add_argument("--version", help="explicit stable version for rollback, e.g. 0.52.205")
    args = parser.parse_args()
    repo = "https://github.com/artokun/comfyui-mcp"
    if args.version:
        version = args.version.removeprefix("v")
        tag = "v" + version
    else:
        release = fetch_json("https://api.github.com/repos/artokun/comfyui-mcp/releases/latest")
        if release["draft"] or release["prerelease"]:
            raise RuntimeError("GitHub returned a draft or prerelease")
        tag = release["tag_name"]
        version = tag.removeprefix("v")
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", version):
        raise RuntimeError(f"Unexpected stable release version: {version!r}")
    # Verify that the release is published to npm before building or restarting.
    package = fetch_json(f"https://registry.npmjs.org/comfyui-mcp/{version}")
    if package["version"] != version:
        raise RuntimeError("npm package does not match the requested release")
    refs = run("git", "ls-remote", repo + ".git", "refs/tags/" + tag,
               "refs/tags/" + tag + "^{}", capture=True)
    commits = {ref: sha for sha, ref in (line.split() for line in refs.splitlines())}
    revision = commits.get("refs/tags/" + tag + "^{}", commits.get("refs/tags/" + tag))
    if not revision:
        raise RuntimeError(f"No Git tag found for {tag}")
    print(f"Building comfyui-mcp:{version} from release {tag} ({revision})", flush=True)
    run("docker", "build", "--pull", "--build-arg", f"MCP_VERSION={version}",
        "--build-arg", f"MCP_REVISION={revision}", "--tag", f"comfyui-mcp:{version}",
        "--tag", "comfyui-mcp:latest", str(Path(__file__).resolve().parent))
    if args.build_only:
        return
    run("composectl", "restart", "ai-comfyui-mcp", "--json")
    expected = run("docker", "image", "inspect", "--format", "{{.Id}}",
                   "comfyui-mcp:latest", capture=True).strip()
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        # systemctl returns before Compose finishes recreating the container.
        # Restrict inspection to containers: the image shares this name.
        result = subprocess.run(
            ["docker", "inspect", "--type", "container", "comfyui-mcp"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            time.sleep(3)
            continue
        container = json.loads(result.stdout)[0]
        state = container["State"]
        health = state.get("Health", {}).get("Status")
        if container["Image"] == expected and state["Running"] and health == "healthy":
            print(f"ComfyUI MCP {version} is running and healthy; ComfyUI was not restarted.")
            return
        if state["Status"] in ("exited", "dead") or health == "unhealthy":
            raise RuntimeError("MCP failed startup; inspect composectl status ai-comfyui-mcp")
        time.sleep(3)
    raise RuntimeError("MCP did not become healthy within 90 seconds")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, OSError, ValueError, KeyError) as error:
        raise SystemExit(f"MCP update failed: {error}") from error
