#!/bin/bash
set -e

echo "Initializing blank state with data checksums enabled..."
initdb -D "$PGDATA" --data-checksums

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE EXTENSION IF NOT EXISTS vector;
EOSQL

echo "PostgreSQL initialization complete."
