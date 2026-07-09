#!/bin/bash
# Single entrypoint for Immich: prepares everything a fresh host needs, then
# starts the stack in the foreground.
#   1. require the database and redis containers to be running
#   2. scaffold the upload directory tree (rootless docker fails the mount
#      permission check no matter what the host permissions are, so the
#      tree and its .immich markers are pre-created)
#   3. ensure the secret files under ${DATA_DIR} exist
#   4. create the database role, database, and extensions on the vchord
#      container (asks for the postgres admin credentials when needed)
#   5. docker compose up
# Idempotent: steps that are already done are skipped.
set -euo pipefail
cd "$(dirname "$0")"

source .env        # DATA_DIR, IMMICH_UPLOAD
[[ -f .env.local ]] && source .env.local
source immich.env  # DB_HOSTNAME, REDIS_HOSTNAME, DB_USERNAME, DB_DATABASE_NAME

db_password_file="${DATA_DIR}/db_password"
api_key_file="${DATA_DIR}/api_key"

require_running() {
    if [[ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null)" != "true" ]]; then
        echo "container '$1' does not exist or is not running, start it first" >&2
        exit 1
    fi
}

require_running "${DB_HOSTNAME}"
require_running "${REDIS_HOSTNAME}"

mkdir -p "${IMMICH_UPLOAD}"/data/{backups,encoded-video,library,profile,thumbs,upload}
for dir in backups encoded-video library profile thumbs upload; do
    touch "${IMMICH_UPLOAD}/data/${dir}/.immich"
done

# Secret files are written without a trailing newline; immich reads them verbatim
if [[ ! -s "${db_password_file}" ]]; then
    (umask 077; printf '%s' "$(openssl rand -hex 24)" > "${db_password_file}")
    echo "generated database password at ${db_password_file}"
fi

if [[ ! -f "${api_key_file}" ]]; then
    (umask 077; : > "${api_key_file}")
    echo "created empty ${api_key_file}, paste an API key from the immich UI into it"
fi

db_password="$(< "${db_password_file}")"

immich_psql() {
    docker exec -i -e PGPASSWORD="${db_password}" "${DB_HOSTNAME}" \
        psql -h 127.0.0.1 -U "${DB_USERNAME}" -d "${DB_DATABASE_NAME}" -qtA "$@"
}

required_extensions() {
    immich_psql -c "SELECT count(*) FROM pg_extension WHERE extname IN ('vchord', 'earthdistance')" 2>/dev/null || true
}

if [[ "$(required_extensions)" == "2" ]]; then
    echo "database already initialized"
else
    read -rp "postgres admin user [postgres]: " admin_user
    admin_user="${admin_user:-postgres}"
    read -rsp "${admin_user} password: " admin_password
    echo

    admin_psql() {
        local db="$1"; shift
        docker exec -i -e PGPASSWORD="${admin_password}" "${DB_HOSTNAME}" \
            psql -h 127.0.0.1 -U "${admin_user}" -d "${db}" -v ON_ERROR_STOP=1 -qtA "$@"
    }

    echo "ensuring role '${DB_USERNAME}' and database '${DB_DATABASE_NAME}'..."
    admin_psql postgres -v user="${DB_USERNAME}" -v pw="${db_password}" -v db="${DB_DATABASE_NAME}" <<'SQL'
SELECT CASE WHEN EXISTS (SELECT FROM pg_roles WHERE rolname = :'user')
    THEN format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'user', :'pw')
    ELSE format('CREATE ROLE %I WITH LOGIN PASSWORD %L', :'user', :'pw')
END
\gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'db', :'user')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'db')
\gexec

SELECT format('ALTER DATABASE %I OWNER TO %I', :'db', :'user')
\gexec
SQL

    # vchord is not a trusted extension, so only a superuser can create it;
    # CASCADE pulls in vector, cube, and earthdistance's dependencies
    echo "ensuring extensions..."
    admin_psql "${DB_DATABASE_NAME}" <<'SQL'
CREATE EXTENSION IF NOT EXISTS vchord CASCADE;
CREATE EXTENSION IF NOT EXISTS earthdistance CASCADE;
SQL

    if [[ "$(required_extensions)" != "2" ]]; then
        echo "bootstrap failed: cannot connect as '${DB_USERNAME}' after setup" >&2
        exit 1
    fi
    echo "database initialized: ${DB_USERNAME}@${DB_HOSTNAME}/${DB_DATABASE_NAME}"
fi

env_files=(--env-file "${HOME}/.config/docker/compose.env" --env-file .env)
[[ -f .env.local ]] && env_files+=(--env-file .env.local)
exec docker compose "${env_files[@]}" up --force-recreate
