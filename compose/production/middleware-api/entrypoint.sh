#!/bin/sh
set -e

CERT_DIR="/certs"
CERT_FILE="$CERT_DIR/tls.crt"
KEY_FILE="$CERT_DIR/tls.key"

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
  mkdir -p "$CERT_DIR"
  openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -subj "/CN=ghostwriter-middleware" \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE"
fi

exec gunicorn \
  --bind 0.0.0.0:8443 \
  --certfile "$CERT_FILE" \
  --keyfile "$KEY_FILE" \
  --access-logfile - \
  --error-logfile - \
  app:app
