# Hollama

Minimal browser-based LLM client, served through Traefik at
`https://hollama.${TRAEFIK_ACME_DOMAIN}` without application or proxy
authentication.

The application stores its settings and conversations in browser storage, so
the container does not need a persistent volume.

## Connect to llama.rs

Add an OpenAI-compatible server in Hollama using the URL from the browser that
is running Hollama. For a browser on the same machine as `llama serve`, use:

```text
http://127.0.0.1:8080/v1
```

The wrapper also exposes llama.cpp's built-in UI directly at
`http://127.0.0.1:8080/`.

If Hollama is opened from another device, expose `llama serve` through a
trusted HTTPS endpoint first; `127.0.0.1` always refers to the browser's own
device.

## Lifecycle

```bash
composectl enable ai-hollama
composectl start ai-hollama
composectl status ai-hollama
```

Upstream image and self-hosting documentation:
<https://github.com/fmaclen/hollama/blob/main/SELF_HOSTING.md>
