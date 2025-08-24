# Docker Compose Project

Welcome to my **Docker Compose Project**!
This repository contains a collection of Docker Compose files, scripts, and configurations to help you orchestrate your development, homelab, or selfhosted environments.

## Features

- Modular Compose files for various services
- Environment-specific configuration support
- Example secrets and `.env` management
- Easy setup and teardown of services

## Getting Started

1. **Clone the repository:**
   ```bash
   git clone https://github.com/delfianto/compose.git
   cd compose
   ```
2. **Copy and populate `.env` files as needed.**
3. **Start your services:**
   ```bash
   docker compose up -d
   ```

## Security Notice

> **Never commit real secrets, API keys, or private keys to this repository!**
> Use `.env.local` or Docker secrets for sensitive data.

## Disclaimer

This project comes **without any warranty** of any kind.
By using this software, you accept all risks, including but not limited to:

- The Borg may invade your neighborhood.
- Your dog may suddenly hate you.
- Coffee may taste slightly more bitter.
- Spontaneous interpretive dance outbreaks are possible.
- The universe may collapse into a potato.

**I am not responsible for any of these (or other) outcomes. Use at your own risk!**

## License

See [LICENSE](LICENSE).
