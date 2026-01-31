#!/bin/bash
set -e

# Initialize with Checksums (if directory is empty)
if [[ ! -s "$PGDATA/PG_VERSION" ]]; then
  echo "Initializing blank state with data checksums enabled..."
  initdb -D "$PGDATA" --data-checksums
fi

# Load the bootstrap library
source "$(dirname "$0")/bootstrap.sh"

# Initialize cluster-wide extensions on the default DB
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE EXTENSION IF NOT EXISTS vector;
EOSQL

# Use the bootstrap function for standard setup
bootstrap_db "openwebui" "" false
bootstrap_db "immich" "vchord cube earthdistance" true

echo "PostgreSQL initialization with checksums and app databases complete."
