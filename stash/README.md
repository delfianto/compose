# Self-Hosted Cultured Media

Welcome, **Man (or Woman) of Culture** 👨‍🎨👩‍🎨

This repository provides a ready-to-use **Docker Compose setup for [StashApp](https://stashapp.cc/)**, the premier personal media server for organizing, browsing, and streaming your, ahem, *highly cultured* media collection.

---

## Features

- **Effortless deployment** – get StashApp running in minutes.
- **Media Library Management** – organize, tag, and rate your videos.
- **Metadata Scraping** – automatic info for your cultured collection.
- **Web UI** – browse your library in style.
- **Optional plugins** – unleash even deeper levels of sophistication.

---

## Quick Start

1. **Clone the project:**
   ```bash
   git clone https://github.com/delfianto/compose.git
   cd stash
   ```

2. **Configure your `.env.local` file as needed.**
   This file contains environment variables used by Docker Compose to configure your StashApp container.

   Example `.env.local`:
   ```env
   UID=1000
   GID=1000

   TRAEFIK_ACME_DOMAIN=yourdomain.app
   DATA_DIR=/path/to/stash/data
   FILE_DIR=/path/to/media/collection
   ```

   **Explanation of variables:**

   - `UID=1000`
     The user ID that the StashApp container runs as.
     Set this to match your host system user so that the container has correct permissions to read/write files.

   - `GID=1000`
     The group ID that the StashApp container runs as.
     Set this to match your host system group for proper filesystem access.

   - `TRAEFIK_ACME_DOMAIN=yourdomain.app`
     If you are using Traefik with ACME (Let's Encrypt) for automatic HTTPS, set this to your domain name.
     Otherwise, you can leave it as is or remove it if not using Traefik.

   - `DATA_DIR=/path/to/stash/data`
     The path on your host where StashApp stores its database, configuration, and thumbnails.
     Set this to a fast disk for best performance.

   - `FILE_DIR=/path/to/media/collection`
     The path on your host where your *media collection* is stored.
     Point this to the location of your videos for StashApp to index and manage.

   > **Note:** Never commit your real `.env.local` to a public repository!
   > This file is for your personal configuration and may contain sensitive information.

3. **Launch StashApp:**
   ```bash
   docker compose up -d
   ```

4. **Open your browser and browse to** [http://localhost:9999](http://localhost:9999)
   *(default port, change as needed in your compose file)*

---

## Disclaimer

This project is provided **as-is**, with no warranty of any kind.
The maintainers are not responsible for:

- Sudden upgrades to your taste in cinema
- Your friends discovering your secret stash
- Your dog no longer respecting you
- Unexpected enlightenment

**Use responsibly, and always remember: you are a person of culture.**
