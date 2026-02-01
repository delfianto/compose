#!/bin/bash

source mariadb.env
source mariadb.env.local

docker exec -it mariadb \
  mariadb -u root -p"$MARIADB_ROOT_PASSWORD" \
  "$MARIADB_DATABASE"
