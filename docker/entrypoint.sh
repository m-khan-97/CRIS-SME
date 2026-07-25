#!/bin/sh
set -eu

python -m cris_sme.api.local_runner \
    --host 127.0.0.1 \
    --port 8787 \
    --output-dir /data/outputs/reports \
    --figure-dir /data/outputs/figures &
RUNNER_PID=$!

trap 'kill -TERM "$RUNNER_PID" 2>/dev/null || true' TERM INT

nginx -g 'daemon off;' &
NGINX_PID=$!

wait -n "$RUNNER_PID" "$NGINX_PID"
