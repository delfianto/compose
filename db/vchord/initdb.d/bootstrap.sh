#!/bin/bash
# Usage as script: ./bootstrap.sh --database name --extensions "ext1 ext2" --superuser
# Usage as library: source bootstrap.sh && bootstrap_db name "ext1 ext2" true

bootstrap_db() {
  local DB_NAME=$1
  local EXTS_STRING=$2
  local IS_SUPERUSER=$3

  # Always perform creation tasks from the default 'postgres' database
  local SYS_PSQL="psql -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d postgres"

  echo "--- Bootstrapping Database: $DB_NAME ---"

  # Create user
  $SYS_PSQL <<-EOSQL
    DO \$\$
    BEGIN
      IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_NAME') THEN
        CREATE ROLE $DB_NAME WITH LOGIN PASSWORD '$POSTGRES_PASSWORD';
      END IF;
    END \$\$;
EOSQL

  # Create database
  $SYS_PSQL -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
    $SYS_PSQL -c "CREATE DATABASE $DB_NAME OWNER $DB_NAME;"

  $SYS_PSQL -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_NAME;"

  # Switch connection to the target database for extensions
  local TARGET_PSQL="psql -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d $DB_NAME"

  if [[ "$IS_SUPERUSER" = true ]]; then
    echo "Granting SUPERUSER privileges to $DB_NAME..."
    $TARGET_PSQL -c "ALTER USER $DB_NAME WITH SUPERUSER;"
    echo
  fi

  # Enable Extensions
  echo "Enabling baseline extension: vector"
  $TARGET_PSQL -c "CREATE EXTENSION IF NOT EXISTS vector;"
  echo

  if [[ ! -z "$EXTS_STRING" ]]; then
    read -ra EXT_ARRAY <<< "$EXTS_STRING"

    for ext in "${EXT_ARRAY[@]}"; do
      clean_ext=$(echo "$ext" | tr -d '"' | tr -d "'")
      if [[ ! -z "$clean_ext" ]]; then
        echo "Enabling extension: $clean_ext"
        $TARGET_PSQL -c "CREATE EXTENSION IF NOT EXISTS $clean_ext CASCADE;"
        echo
      fi
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
