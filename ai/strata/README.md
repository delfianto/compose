# Strata

Builds the upstream NVIDIA Dockerfile at the release tag in `.env`.
The image is compiled for the build host's CPU, RTX 3060 (CUDA arch 86),
and RTX 4080 (CUDA arch 89). Both GPUs are exposed through CDI.
`docker-bake.hcl` owns the build definition; `compose.yaml` owns runtime
configuration. The source release is `v0.1.41` and the image is
`ghcr.io/delfianto/strata:v0.1.41` by default. This is a local image tag;
building does not publish it to GHCR.

```sh
./compose.sh config --quiet
./build.sh --print
./build.sh strata
```

`./compose.sh` loads existing host-wide defaults, `.env`, and `.env.local`
in that order, so `DATA_DIR=/mnt/sata1/models/strata` wins over the tracked
`/srv/appdata/strata` default. Updated `compose-utils` uses the same file order
automatically. Shell environment variables still take precedence for direct
commands, as usual with Compose.

`./build.sh` exports the shell-compatible `.env` and then `.env.local` for
Bake's HCL variables. `./compose.sh build strata` also routes to Bake.
To update, set `STRATA_VERSION` to a published upstream release tag in
`.env` or `.env.local` and rebuild. The image is loaded into local Docker.

The `/data` bind mount holds downloads, inference packs, MTP assets, and
persistent configuration. IQ3_S downloads about 83.6 GB plus about 6 GB
for MTP, and preparation needs additional disk space. A container start
downloads the model; the image build does not. Setup uses substantial
system RAM and GPUs 0 and 1, shared with other services on this host.

## Rootless Docker

See the repository's [rootless Docker guidance](../../README.md#rootless-docker).
Prepare the data directory before starting:

```sh
mkdir -p /mnt/sata1/models/strata
```

Strata uses `user: "0:0"`, `MEMLOCK_BYTES=34359738368`, and the local
runtime override `STRATA_ARENA_PIN_GIB=32`. Performance with partial
arena pinning still needs an inference benchmark.

## Dual GPU configuration

`GPUS=0,1` and `LAYER_SPLIT=auto` enable the layer split. In v0.1.41,
auto orders the faster GPU last (the 4080 runs the output head and MTP),
then searches layer boundaries using free VRAM and weighted expert-cache
coverage. This is not a 16:12 tensor split and needs no NVLink or P2P.
The engine startup log reports the actual order, boundary, and cache sizes.
The 3060 is on a PCIe x4 link on this host; leave PCIe probing automatic.

`STRATA_SPLIT_OWN=auto` applies upstream's prompt-buffer heuristic rather
than forcing separate buffers on a full card. Context stays at 32K,
vision stays off, and INT8 KV preserves the quality-oriented baseline.
No batch slots are enabled: this configuration targets single-response
latency rather than concurrent-client throughput.

The local runtime override `LOW_RAM=on` selects the resident low-RAM
variant where the remaining experts fit. Since v0.1.40 this works on a
split: experts held by either GPU need not also occupy the CPU arena.
It may create an additional experts pack on disk. Confirm the startup log
says resident mode, rather than mmap/file reads, before judging speed.

Actual performance tuning still requires a downloaded model. Compare the
4080 alone with the pair using identical short and long prompts, plus at
least three warm runs. Record prompt and decode throughput separately,
first-token latency, GPU cache hits, available RAM, and answer correctness.
Auto optimizes expert placement, not measured end-to-end latency; a slower
3060 can still reduce decoding throughput for some workloads.

After measuring auto's chosen boundary K, test nearby explicit boundaries
and `STRATA_STAGE_TRIM=1` (only supported with explicit split points).
Explicit boundaries are layer indices, not VRAM ratios; retain auto's GPU
order explicitly before comparing, since manual splits keep the given order.
Then benchmark `--pipeline-windows 2` and `--adapt-async 1` individually
in the saved config's `args`. These are opt-in and can spend extra VRAM or
change rounding/cache placement; retain only settings that improve real
tasks without harming answer quality. `STRATA_PREFILL_HELP=1` and fused
prompt kernels are additional alternatives to test, not switches to stack
blindly. Do not mix layer splitting with `--peer-device` or helper-GPU
cache modes, and do not set `--remote-expert-opt` for a plain split: it is inert.

References checked for this setup:
- https://github.com/Niko1221/Strata/blob/v0.1.41/docs/MULTI_GPU.md
- https://github.com/Niko1221/Strata/issues/1352 (card ordering)
- https://github.com/Niko1221/Strata/issues/253 (Linux pinned RAM)
- https://github.com/Niko1221/Strata/blob/v0.1.41/bench/results/2026-09-29-layer-split/README.md

Runtime choices live in `strata.env`, with optional overrides in
`strata.env.local`. Once configured, changing setup choices requires a
temporary `REINSTALL=1` runtime override. The upstream image supplies
the `/health` healthcheck. Shutdown has a 60-second grace period.

Traefik serves `https://strata.${TRAEFIK_ACME_DOMAIN}`, with an
OpenAI-compatible API at `/v1`, using the `websecure` entrypoint and
Cloudflare certificate resolver. It connects to Strata's internal port
8080 through the external `proxy` network. No host port is published.
Homepage discovers the service through its labels. Containers on `genai`
can also reach `http://strata:8080/v1`. The external `proxy` network
permits outbound model downloads.

`compose-utils` also loads `.env.local` for this project's systemd commands.
This project has not been enabled at boot.

Upstream: https://github.com/Niko1221/Strata
