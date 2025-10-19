#!/bin/bash
set -e

# These are the environment variables passed to the container
POSTGRES_PASSWORD="${POSTGRES_PASSWORD}"
POSTGRES_USER="${POSTGRES_USER}"
POSTGRES_DB="${POSTGRES_DB}"

# Initialize the database
initdb --data-checksums -D /var/lib/postgresql/data

# Debugging: Print environment variables
echo "Environment Variables:"
echo "  - POSTGRES_DB: $POSTGRES_DB"
echo "  - POSTGRES_USER: $POSTGRES_USER"
echo "  - POSTGRES_PASSWORD: $POSTGRES_PASSWORD"

# Create a new user and database for Open WebUI
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE USER openwebui WITH PASSWORD '$POSTGRES_PASSWORD';"
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE DATABASE openwebui OWNER openwebui;"
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "GRANT ALL PRIVILEGES ON DATABASE openwebui TO openwebui;"

# Create a new user and database for LiteLLM
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE USER litellm WITH PASSWORD '$POSTGRES_PASSWORD';"
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE DATABASE litellm OWNER litellm;"
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "GRANT ALL PRIVILEGES ON DATABASE litellm TO litellm;"
