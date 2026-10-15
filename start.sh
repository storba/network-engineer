#!/usr/bin/env bash
# Bring the lab up and block until site-to-site forwarding works.
# Run this inside the Debian VM, from anywhere:
#   ./start.sh
set -euo pipefail
cd "$(dirname "$0")"

if ! docker compose version >/dev/null 2>&1; then
    echo "docker compose is not available. Run this on the Debian VM, not the Ubuntu host." >&2
    exit 1
fi

echo "Starting containers (allow_bridged, routers, hosts, provisioner)..."
docker compose up -d --build

provisioner_ok() {
    local code
    code="$(docker inspect -f '{{.State.ExitCode}}' provisioner 2>/dev/null || echo 1)"
    [ "$code" = "0" ] && docker logs provisioner 2>&1 | tail -30 | grep -q "provisioning complete"
}

echo "Waiting for the provisioner to push IPsec, VXLAN, routes, and NAT..."
attempt=1
while [ "$attempt" -le 3 ]; do
    state="$(docker inspect -f '{{.State.Status}}' provisioner 2>/dev/null || echo missing)"
    if [ "$state" = "running" ]; then
        docker wait provisioner >/dev/null || true
    elif ! provisioner_ok; then
        echo "Provisioner is not finished (attempt ${attempt}). Starting it again..."
        docker start provisioner >/dev/null
        docker wait provisioner >/dev/null || true
    fi
    if provisioner_ok; then
        echo "Provisioning complete."
        break
    fi
    echo "Provisioner exited without success:"
    docker logs provisioner 2>&1 | tail -20
    attempt=$((attempt + 1))
    sleep 5
done
if ! provisioner_ok; then
    echo "Provisioner failed. Fix the log above, then run ./start.sh again." >&2
    exit 1
fi

echo "Waiting for edge default routes to use the overlays..."
ready=0
for _ in $(seq 1 30); do
    route_a="$(docker exec edge_router_a ip route show default 2>/dev/null || true)"
    route_b="$(docker exec edge_router_b ip route show default 2>/dev/null || true)"
    case "$route_a" in
        *10.255.10.2*)
            case "$route_b" in
                *10.255.20.2*)
                    if docker exec host_1a_1 ping -c 1 -W 2 192.168.4.10 >/dev/null 2>&1 \
                        && docker exec host_1b_1 ping -c 1 -W 2 192.168.2.10 >/dev/null 2>&1; then
                        ready=1
                        break
                    fi
                    ;;
            esac
            ;;
    esac
    # Boot may still have Docker's management default. Put the overlay back.
    docker exec edge_router_a ip route replace default via 10.255.10.2 dev vti0 >/dev/null 2>&1 || true
    docker exec edge_router_b ip route replace default via 10.255.20.2 dev vxlan0 >/dev/null 2>&1 || true
    sleep 2
done
if [ "$ready" -ne 1 ]; then
    echo "Overlays are not forwarding yet." >&2
    echo "edge A default: ${route_a:-missing}" >&2
    echo "edge B default: ${route_b:-missing}" >&2
    exit 1
fi

echo "Lab is ready. Running connectivity tests..."
python3 -m unittest test_connectivity.py -v
