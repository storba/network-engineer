# Site-to-site lab

Docker Compose lab with a central VyOS router, two edge routers, and eight hosts. Site A uses an IPsec VTI overlay; Site B uses VXLAN. Central NATs only Subnet1A and Subnet1B to the internet.

```text
                         INTERNET
                             |
                      central_router
                     /              \
            IPsec overlay      VXLAN overlay
                   /                  \
          edge_router_a            edge_router_b
           /        \               /        \
     Subnet1A    Subnet2A     Subnet1B    Subnet2B
    192.168.2.0  192.168.1.0  192.168.4.0  192.168.3.0
```

Tested in a **Debian VM on Linux**. Run Docker and the tests **inside that VM** (this repo can be bind-mounted into the VM). Docker on the Linux host is not required.

## Requirements

On the Debian VM:

- Docker Engine with Compose v2 (`docker compose`)
- Python 3 (stdlib only; used for tests)
- Ability to run privileged containers and bind-mount `/lib/modules` (VyOS)

The current user must be able to run `docker` without extra wrappers.

## Start the lab

From the repo root on the VM:

```bash
./start.sh
```

That is the whole startup. It runs `docker compose up -d --build`, waits until the provisioner prints `provisioning complete` (and starts it again if VyOS was not ready), then waits until Site A and Site B can ping each other and runs the tests.

`docker compose up -d` returns while VyOS is still booting. Running the tests in that window fails even though the containers are up. `docker compose logs -f provisioner` only shows logs; it does not finish startup. `allow_bridged` is started by Compose and must stay running.

## Run the tests

Still on the VM, from the repo root, after provisioning has finished:

```bash
python3 -m unittest test_connectivity.py -v
```

The script uses `docker exec` and ICMP (`ping -c 1 -W 2`) to check:

| Layer | What it verifies |
| --- | --- |
| Lab up | Host and router containers are running |
| Same subnet | Hosts ping their LAN peer |
| Intra-site | Hosts reach the other local subnet via the edge router |
| WAN | Edge ↔ central P2P links (`1.1.1.0/30`, `1.1.2.0/30`) |
| Overlay | IPsec VTI (`10.255.10.0/30`) and VXLAN (`10.255.20.0/24`) |
| Site-to-site | Hosts A ↔ B on both subnet1 and subnet2 |
| NAT | Subnet1A/1B reach the internet; Subnet2A/2B do not; central reaches `203.0.113.254` |

Internet probes default to `8.8.8.8`. Override if needed:

```bash
LAB_INTERNET_IP=9.9.9.9 python3 -m unittest test_connectivity.py -v
```

## Stop

```bash
docker compose down
```
## if error
```bash
docker compose down --remove-orphans

docker network inspect $(docker network ls -q) --format '{{.Name}} {{range .IPAM.Config}}{{.Subnet}}{{end}}' | grep -E '1\.1\.|192\.168\.|10\.0\.0\.|203\.0\.113'

docker network rm site-to-site_net_wan_b net_wan_b \
  site-to-site_net_wan_a net_wan_a 2>/dev/null

docker compose up -d --build
```

##
cap_add:
    - NET_ADMIN
    - SYS_ADMIN
    - SYS_MODULE