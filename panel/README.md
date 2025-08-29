### **Self-Hosted Service with Domain Name**

This project provides a robust foundation for self-hosting services using Docker Compose, integrating Traefik as a reverse proxy and Portainer for container management. The stack is configured for automatic SSL certificate management using Let's Encrypt and the Cloudflare DNS challenge, ensuring secure HTTPS connections for all your services.

-----

### **1. Core Components & Domain Addresses**

The project is designed with modularity in mind, using three separate Docker Compose files that are included by a central `compose.yml`.

| Component | Function | Domain Address |
| :--- | :--- | :--- |
| **Traefik** | Reverse Proxy, SSL, and routing management. | `https://traefik.yourdomain.app` |
| **Portainer** | Web-based Docker environment management. | `https://panel.yourdomain.app` |

**Note**: `yourdomain.app` is a placeholder for your actual domain, which is defined in the `.env.local` file.

-----

### **2. Getting Started: Prerequisites**

Before you can deploy this stack, ensure you have the following ready:

  * **Docker & Docker Compose**: Installed on your server.
  * **Cloudflare Account**: With a registered domain name (e.g., `yourdomain.app`).
  * **Cloudflare API Token**: A token with **`Zone:Read`** and **`DNS:Edit`** permissions for your domain. This is crucial for the DNS challenge to work.

-----

### **3. Cloudflare Setup: Domain and API Token**

1.  **Add Your Domain to Cloudflare**:

      * Sign up for a Cloudflare account.
      * Add your domain and select the **Free** plan.
      * Cloudflare will provide you with two unique nameservers. Update your domain registrar's nameservers to these new ones.
      * This process delegates DNS management to Cloudflare.

2.  **Add Necessary DNS Records**:

      * Navigate to the **"DNS"** tab for your domain in the Cloudflare dashboard.
      * **Wildcard A Record**: Create an **A** record with the name `*` and point it to your server's public IP address. Ensure the **Proxy status** is set to **"DNS only"** (gray cloud).
      * **Root Domain A Record**: Create another **A** record with the name `@` and point it to your server's public IP address.

3.  **Generate the Cloudflare API Token**:

      * Go to **"My Profile" \> "API Tokens"** in your Cloudflare dashboard.
      * Click **"Create Token"**.
      * Select the **"Edit zone DNS"** template.
      * Under **"Zone Resources"**, select **"Specific zone"** and choose your domain.
      * Click **"Create Token"**. **Copy the token immediately** as it will not be shown again. This is the token you will use for your Traefik setup.

-----

### **4. Configuration**

1.  **Create `.env.local` file:** This file stores all your custom settings. Create it in the root directory of your project and populate it with your information.

    ```env
    # User and Group IDs for container permissions
    # UID and GID should match the user who owns the project files
    UID=1000
    GID=947

    # Root directory on your host to store all application data
    DATA_DIR=/path/to/your/data

    # Your domain name registered with Cloudflare
    TRAEFIK_ACME_DOMAIN=yourdomain.app

    # Email address for Let's Encrypt notifications
    TRAEFIK_ACME_EMAIL=your.email@example.com
    ```

2.  **Create Secrets Files:** Traefik uses two secret files for security. Place both of these files in the directory specified by your `DATA_DIR` variable (e.g., `/path/to/your/data/traefik/`).

      * `cf_dns_api_token`: Create this file and paste your Cloudflare API token inside it.
      * `htpasswd`: Create this file and add a username and password using an `htpasswd` generator. This will be used to protect the Traefik dashboard.

-----

### **5. Deployment**

To start the entire application stack, run the following command. This command explicitly tells Docker Compose to use both the `.env` and `.env.local` files and ensures all services are recreated with the new configuration.

```bash
docker compose --file compose.yml --env-file .env --env-file .env.local up --force-recreate -d
```

-----

### **6. Troubleshooting**

If you encounter issues, the first and most important step is to check the Traefik logs.

```bash
docker compose logs -f traefik
```

A common issue is the `TRAEFIK DEFAULT CERT` error, which means the DNS challenge for a trusted SSL certificate failed. This is most often caused by a **DNS propagation delay** or incorrect Cloudflare API token permissions. If this happens, wait a few minutes and re-run the `docker compose` command. The logs will provide specific details on the cause of the failure.
