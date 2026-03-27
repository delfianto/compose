#!/bin/bash
# This is only needed for rootles docker since the permission check keeps failing
# no matter what the permission of the actual host directory, so just YOLO it
# ~ yeah it failed even with given 777 permission ~

source .env
mkdir -p ${IMMICH_UPLOAD}/{backups,encoded-video,library,profile,thumbs,upload}

for dir in backups encoded-video library profile thumbs upload; do
    touch "${IMMICH_UPLOAD}/data/${dir}/.immich"
done
