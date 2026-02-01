#!/bin/bash
# Usage: ./collation.sh --database "immich openwebui candlekeep"

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --database) DB_LIST="$2"; shift ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
  shift
done

if [[ -z "$DB_LIST" ]]; then
  echo "Usage: ./collation.sh --database \"db1 db2 db3\""
  exit 1
fi

# Function to perform live maintenance
live_maint() {
  local db=$1
  echo "--- [LIVE] Maintenance for: $db ---"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" <<-EOSQL
    REINDEX DATABASE "$db";
    ALTER DATABASE "$db" REFRESH COLLATION VERSION;
EOSQL
}

# Function to perform offline maintenance
offline_maint() {
  local db=$1
  echo "--- [OFFLINE] Single-User Maintenance for: $db ---"
  # Note: Using gosu to ensure the binary isn't run as root
  gosu postgres postgres --single -D /var/lib/postgresql/18/docker "$db" <<-EOF
    REINDEX DATABASE "$db";
    ALTER DATABASE "$db" REFRESH COLLATION VERSION;
EOF
}

# Detect Server State
# pg_isready returns 0 if the server is accepting connections
if pg_isready -q; then
  echo "PostgreSQL server is running. Using standard connection..."
  for db in $DB_LIST; do
    live_maint "$db"
  done
else
  echo "PostgreSQL server is NOT running. Using Single-User mode..."
  for db in $DB_LIST; do
    offline_maint "$db"
  done
fi

echo "Collation and Reindexing complete."
