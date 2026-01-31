#!/bin/bash

if [[ -f .env ]]; then source .env; fi
if [[ -f ./env/vchord.env.local ]]; then source ./env/vchord.env.local; fi

usage() {
  echo "Usage:"
  echo "  Connect to shell:  ./connect.sh --database foo"
  echo "  Bootstrap new DB:  ./connect.sh --bootstrap bar --extensions \"ext1 ext2\" [--superuser]"
  exit 1
}

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --database) TARGET_DB="$2"; shift ;;
    --bootstrap) BOOTSTRAP_DB="$2"; shift ;;
    --extensions) EXTS="$2"; shift ;;
    --superuser) SUPER=true ;;
    *) usage ;;
  esac
  shift
done

# Just connect to a specific database shell
if [[ ! -z "$TARGET_DB" && -z "$BOOTSTRAP_DB" ]]; then
  echo "--- Connecting to Database Shell: $TARGET_DB ---"
  docker exec -it vchord psql -U "$POSTGRES_USER" -d "$TARGET_DB"
  exit 0
fi

# Connect and perform bootstrap
if [[ ! -z "$BOOTSTRAP_DB" ]]; then
  BOOTSTRAP_ARGS="--database $BOOTSTRAP_DB"

  if [[ ! -z "$EXTS" ]]; then BOOTSTRAP_ARGS="$BOOTSTRAP_ARGS --extensions \"$EXTS\""; fi
  if [[ "$SUPER" = true ]]; then BOOTSTRAP_ARGS="$BOOTSTRAP_ARGS --superuser"; fi

  echo "--- Triggering Remote Bootstrap for: $BOOTSTRAP_DB ---"
  docker exec -it vchord /docker-entrypoint-initdb.d/bootstrap.sh $BOOTSTRAP_ARGS
  exit 0
fi

usage
