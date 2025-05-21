#!/bin/sh
set -e

CERT_DIR=/certs
KEY=$CERT_DIR/key.pem
CRT=$CERT_DIR/cert.pem

need_regen() {
  # 1) missing file?
  [ ! -f "$KEY" ] || [ ! -f "$CRT" ] && return 0

  # 2) expired (or will expire in the next 24h)?
  #    -checkend seconds: returns false if cert expires within that window
  if ! openssl x509 -in "$CRT" -noout -checkend $((24 * 3600)); then
    echo "[entrypoint] Certificate expired or expiring within 24h."
    return 0
  fi

  # 3) key+cert mismatch?
  cert_mod=$(openssl x509 -noout -modulus -in "$CRT" | openssl md5)
  key_mod=$(openssl rsa  -noout -modulus -in "$KEY" | openssl md5)
  if [ "$cert_mod" != "$key_mod" ]; then
    echo "[entrypoint] Private key and certificate do not match."
    return 0
  fi

  return 1
}

if need_regen; then
  echo "[entrypoint] Generating new self-signed cert…"
  mkdir -p "$CERT_DIR"
  openssl req -x509 -nodes -days 365 \
    -newkey rsa:2048 \
    -keyout "$KEY" \
    -out "$CRT" \
    -subj "/CN=${HOSTNAME:-localhost}"
else
  echo "[entrypoint] Valid cert/key found, skipping generation."
fi

exec "$@"
