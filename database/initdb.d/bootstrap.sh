#!/bin/bash
# Usage as script: ./bootstrap.sh --database name --extensions "ext1 ext2" --superuser
# Usage as library: source bootstrap.sh && bootstrap_db name "ext1 ext2" true

bootstrap_db() {
  local DB_NAME=$1
  local EXTENSIONS=$2
  local IS_SUPERUSER=$3
  local PSQL_CMD="psql -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d $DB_NAME"

  echo "--- Bootstrapping Database: $DB_NAME ---"

  # Create User and Database
  $PSQL_CMD <<-EOSQL
    CREATE USER $DB_NAME WITH PASSWORD '$POSTGRES_PASSWORD';
    CREATE DATABASE $DB_NAME OWNER $DB_NAME;
    GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_NAME;
EOSQL

  # Handle Superuser status
  if [ "$IS_SUPERUSER" = true ]; then
    echo "Granting SUPERUSER privileges to $DB_NAME..."
    $PSQL_CMD -c "ALTER USER $DB_NAME WITH SUPERUSER;"
  fi

  # Enable Extensions
  local DB_PSQL="psql -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d $DB_NAME"
  $DB_PSQL -c "CREATE EXTENSION IF NOT EXISTS vector;"

  if [[ ! -z "$EXTENSIONS" ]]; then
    for ext in $EXTENSIONS; do
      echo "Enabling extension: $ext"
      $DB_PSQL -c "CREATE EXTENSION IF NOT EXISTS $ext CASCADE;"
    done
  fi
}

# CLI parsing logic (if script is executed directly)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  DB_NAME=""
  EXTS=""
  SUPER=false

  while [[ "$#" -gt 0 ]]; do
    case $1 in
      --database) DB_NAME="$2"; shift ;;
      --extensions) EXTS="$2"; shift ;;
      --superuser) SUPER=true ;;
    esac
    shift
  done

  if [[ -z "$DB_NAME" ]]; then
    echo "Usage: --database [name] --extensions \"exts\" [--superuser]"
    exit 1
  fi

  bootstrap_db "$DB_NAME" "$EXTS" "$SUPER"
fi
