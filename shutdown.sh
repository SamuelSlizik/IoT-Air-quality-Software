#!/usr/bin/env sh
set -e

# these env-vars come from your docker-compose.yml
: "${SSH_HOST:?Need to set SSH_HOST}"
: "${SSH_USER:?Need to set SSH_USER}"
: "${SSH_PASSWORD:?Need to set SSH_PASSWORD}"
: "${SSH_PORT:=22}"

# run the remote shutdown
sshpass -p "$SSH_PASSWORD" \
  ssh -o StrictHostKeyChecking=no \
      -p "$SSH_PORT" \
      "$SSH_USER@$SSH_HOST" \
  "sudo shutdown -h now"