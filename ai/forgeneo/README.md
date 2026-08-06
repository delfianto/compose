# Stable Diffusion WebUI Forge Neo

The Compose project lives at `ai/forgeneo`; both its service and container are
named `forgeneo` to follow the repository's service-naming convention.

Forge Neo runs as an independent inference application on `cuda:0`. Its
`--forge-ref-comfy-home /comfyui` option scans the read-only ComfyUI data mount
for compatible model directories, including `checkpoints`,
`diffusion_models`/`unet`, `clip`/`text_encoders`, `loras`, `vae`, and
`controlnet`.

The shared host layout is rooted at `/srv/appdata/comfyui` and is configured by
`DATA_DIR` in `.env`. Models added there are available to both applications;
Forge's virtual environment and package cache remain isolated under
`/srv/appdata/forgeneo`.

This is filesystem-level model sharing. Forge does not submit workflows to the
ComfyUI API or use the ComfyUI container as its backend, so the services do not
need a network or systemd dependency on each other.

Generated images remain in `${HOME}/Pictures/StableDiffusion`.
