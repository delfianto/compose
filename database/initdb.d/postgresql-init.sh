#!/bin/bash
set -e

# These are the environment variables passed to the container
POSTGRES_PASSWORD="${POSTGRES_PASSWORD}"
POSTGRES_USER="${POSTGRES_USER}"
POSTGRES_DB="${POSTGRES_DB}"

# Initialize the database
initdb -D /var/lib/postgresql/data --data-checksums

# Debugging: Print environment variables
echo "Environment Variables:"
echo "  - POSTGRES_DB: $POSTGRES_DB"
echo "  - POSTGRES_USER: $POSTGRES_USER"
echo "  - POSTGRES_PASSWORD: $POSTGRES_PASSWORD"

# Enable the vector extension on the default database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
EOSQL

# Create a new user and database for OpenWebUI
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER openwebui WITH PASSWORD '$POSTGRES_PASSWORD';
    CREATE DATABASE openwebui OWNER openwebui;
    GRANT ALL PRIVILEGES ON DATABASE openwebui TO openwebui;
EOSQL

# Enable vector extension on the openwebui database too
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "openwebui" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
EOSQL

echo "Vector extension enabled on both databases"
