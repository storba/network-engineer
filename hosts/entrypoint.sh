#!/bin/sh
set -u

if [ -n "${GATEWAY:-}" ]; then
    attempts=0
    while [ "$attempts" -lt 30 ]; do
        if ip route replace default via "$GATEWAY"; then
            break
        fi
        attempts=$((attempts + 1))
        sleep 1
    done
fi

exec sleep infinity
