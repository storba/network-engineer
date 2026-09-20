#!/usr/bin/env python3
"""Push IPsec, VXLAN, routes and NAT to VyOS via the HTTP API."""

from __future__ import annotations

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

CTX = ssl._create_unverified_context()
TIMEOUT = 180
SLEEP = 5


def load_config() -> dict:
    path = Path(os.environ.get("CONFIG", "/config.yml"))
    return yaml.safe_load(path.read_text())


def api(base: str, key: str, endpoint: str, payload) -> dict:
    boundary = "----vyosboundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="key"\r\n\r\n{key}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="data"\r\n\r\n'
        f"{json.dumps(payload)}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        f"{base}/{endpoint}",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, context=CTX, timeout=120) as resp:
        raw = resp.read().decode()
    return json.loads(raw) if raw else {}


def wait_for_api(base: str, key: str) -> None:
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        try:
            api(base, key, "retrieve", {"op": "showConfig", "path": []})
            print(f"API ready: {base}", flush=True)
            return
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
            print(f"waiting for {base}: {err}", flush=True)
            time.sleep(SLEEP)
    raise SystemExit(f"API not reachable: {base}")


def set_cmd(path: list, value=None) -> dict:
    cmd = {"op": "set", "path": [str(p) for p in path]}
    if value is not None:
        cmd["value"] = str(value)
    return cmd


def configure_router(name: str, base: str, key: str, commands: list[dict]) -> None:
    print(f"configuring {name} ({len(commands)} commands)", flush=True)
    try:
        result = api(base, key, "configure", commands)
    except urllib.error.HTTPError as err:
        body = err.read().decode() if err.fp else ""
        raise SystemExit(f"{name} configure HTTP {err.code}: {body}") from err
    print(f"{name} configure: {result}", flush=True)
    if result.get("success") is False:
        raise SystemExit(f"{name} configure failed: {result.get('error')}")
    try:
        saved = api(base, key, "config-file", {"op": "save"})
        print(f"{name} save: {saved}", flush=True)
    except urllib.error.HTTPError as err:
        body = err.read().decode() if err.fp else ""
        print(f"{name} save skipped: HTTP {err.code} {body}", flush=True)


def ipsec_commands(local: str, remote: str, vti_addr: str, psk: str, wan_if: str) -> list[dict]:
    return [
        set_cmd(["vpn", "ipsec", "ipsec-interfaces", "interface", wan_if]),
        set_cmd(["vpn", "ipsec", "options", "disable-route-autoinstall"]),
        set_cmd(["vpn", "ipsec", "ike-group", "IKE-LAB", "key-exchange", "ikev2"]),
        set_cmd(["vpn", "ipsec", "ike-group", "IKE-LAB", "lifetime", "3600"]),
        set_cmd(["vpn", "ipsec", "ike-group", "IKE-LAB", "proposal", "1", "encryption", "aes256"]),
        set_cmd(["vpn", "ipsec", "ike-group", "IKE-LAB", "proposal", "1", "hash", "sha256"]),
        set_cmd(["vpn", "ipsec", "ike-group", "IKE-LAB", "proposal", "1", "dh-group", "14"]),
        set_cmd(["vpn", "ipsec", "esp-group", "ESP-LAB", "lifetime", "1800"]),
        set_cmd(["vpn", "ipsec", "esp-group", "ESP-LAB", "pfs"], "dh-group14"),
        set_cmd(["vpn", "ipsec", "esp-group", "ESP-LAB", "proposal", "1", "encryption", "aes256"]),
        set_cmd(["vpn", "ipsec", "esp-group", "ESP-LAB", "proposal", "1", "hash", "sha256"]),
        set_cmd(["interfaces", "vti", "vti0", "address"], vti_addr),
        set_cmd(["vpn", "ipsec", "site-to-site", "peer", remote, "authentication", "mode", "pre-shared-secret"]),
        set_cmd(["vpn", "ipsec", "site-to-site", "peer", remote, "authentication", "pre-shared-secret", psk]),
        set_cmd(["vpn", "ipsec", "site-to-site", "peer", remote, "ike-group", "IKE-LAB"]),
        set_cmd(["vpn", "ipsec", "site-to-site", "peer", remote, "local-address", local]),
        set_cmd(["vpn", "ipsec", "site-to-site", "peer", remote, "vti", "bind", "vti0"]),
        set_cmd(["vpn", "ipsec", "site-to-site", "peer", remote, "vti", "esp-group", "ESP-LAB"]),
    ]


def vxlan_commands(addr: str, vni: int, port: int, source: str, remote: str) -> list[dict]:
    return [
        set_cmd(["interfaces", "vxlan", "vxlan0", "address"], addr),
        set_cmd(["interfaces", "vxlan", "vxlan0", "vni"], vni),
        set_cmd(["interfaces", "vxlan", "vxlan0", "port"], port),
        set_cmd(["interfaces", "vxlan", "vxlan0", "source-address"], source),
        set_cmd(["interfaces", "vxlan", "vxlan0", "remote"], remote),
    ]


def static_route(prefix: str, nexthop: str) -> dict:
    return set_cmd(["protocols", "static", "route", prefix, "next-hop", nexthop])


def nat_commands(outbound: str, sources: list[str]) -> list[dict]:
    cmds = []
    for i, src in enumerate(sources, start=10):
        cmds.extend(
            [
                set_cmd(["nat", "source", "rule", str(i), "outbound-interface", outbound]),
                set_cmd(["nat", "source", "rule", str(i), "source", "address", src]),
                set_cmd(["nat", "source", "rule", str(i), "translation", "address", "masquerade"]),
            ]
        )
    return cmds


def main() -> int:
    cfg = load_config()
    key = cfg["api"]["key"]
    port = cfg["api"]["port"]
    mgmt = cfg["mgmt"]

    edge_a = f"https://{mgmt['edge_a']}:{port}"
    edge_b = f"https://{mgmt['edge_b']}:{port}"
    central = f"https://{mgmt['central']}:{port}"

    for name, base in [("edge-a", edge_a), ("edge-b", edge_b), ("central", central)]:
        wait_for_api(base, key)

    ipsec = cfg["ipsec"]
    vxlan = cfg["vxlan"]
    a1 = cfg["site_a"]["subnet1"]["cidr"]
    a2 = cfg["site_a"]["subnet2"]["cidr"]
    b1 = cfg["site_b"]["subnet1"]["cidr"]
    b2 = cfg["site_b"]["subnet2"]["cidr"]

    configure_router(
        "edge-a",
        edge_a,
        key,
        ipsec_commands(
            ipsec["local_wan"],
            ipsec["remote_wan"],
            f"{ipsec['vti']['edge_a']}/30",
            ipsec["psk"],
            "eth3",
        )
        + [static_route("0.0.0.0/0", ipsec["vti"]["central"])],
    )

    configure_router(
        "edge-b",
        edge_b,
        key,
        vxlan_commands(
            f"{vxlan['overlay']['edge_b']}/24",
            vxlan["vni"],
            vxlan["port"],
            vxlan["local_wan"],
            vxlan["remote_wan"],
        )
        + [static_route("0.0.0.0/0", vxlan["overlay"]["central"])],
    )

    configure_router(
        "central",
        central,
        key,
        ipsec_commands(
            ipsec["remote_wan"],
            ipsec["local_wan"],
            f"{ipsec['vti']['central']}/30",
            ipsec["psk"],
            "eth2",
        )
        + vxlan_commands(
            f"{vxlan['overlay']['central']}/24",
            vxlan["vni"],
            vxlan["port"],
            vxlan["remote_wan"],
            vxlan["local_wan"],
        )
        + [
            static_route(a1, ipsec["vti"]["edge_a"]),
            static_route(a2, ipsec["vti"]["edge_a"]),
            static_route(b1, vxlan["overlay"]["edge_b"]),
            static_route(b2, vxlan["overlay"]["edge_b"]),
            static_route("0.0.0.0/0", cfg["internet"]["gateway"]),
        ]
        + nat_commands(cfg["nat"]["outbound_interface"], cfg["nat"]["sources"]),
    )
    print("provisioning complete", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
