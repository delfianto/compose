#!/bin/bash
docker compose --env-file ~/.config/docker/compose.env --env-file .env --env-file .env.local up
