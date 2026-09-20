#!/bin/sh
set -eu

# Docker "internal" networks drop bridged frames whose dest IP is outside
# the bridge subnet. A router on two such networks must receive those
# frames (dest MAC is the router) so it can forward between LANs.
if ! iptables -C DOCKER-USER -m physdev --physdev-is-bridged -j ACCEPT 2>/dev/null; then
    iptables -I DOCKER-USER -m physdev --physdev-is-bridged -j ACCEPT
fi

echo "DOCKER-USER: accepted bridged traffic"
exec sleep infinity
