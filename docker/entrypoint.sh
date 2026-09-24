#!/bin/sh
set -eu

mkdir -p /data/outputs/reports /data/outputs/figures
exec python -m cris_sme.api.supervisor
