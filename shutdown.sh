#!/usr/bin/env sh
set -e

# run the remote shutdown
sshpass -p "Samo1samo" \
  ssh -o StrictHostKeyChecking=no \
      -p "22" \
      "samo@host.docker.internal" \
  "sudo shutdown -h now"