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

# DOCX generation + LibreOffice PDF conversion run far past gunicorn's default
# 30s worker timeout, which kills the worker mid-request and surfaces as a 500.
exec gunicorn \
  --bind 0.0.0.0:8443 \
  --certfile "$CERT_FILE" \
  --keyfile "$KEY_FILE" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-900}" \
  --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-60}" \
  --access-logfile - \
  --error-logfile - \
  app:app
