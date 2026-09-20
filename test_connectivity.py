#!/usr/bin/env python3
"""Connectivity checks for the site-to-site lab via local docker exec."""

from __future__ import annotations

import os
import subprocess
import unittest

PING_COUNT = "1"
PING_WAIT = "2"
INTERNET_IP = os.environ.get("LAB_INTERNET_IP", "8.8.8.8")

HOST_1A_1 = "host_1a_1"
HOST_1A_2 = "host_1a_2"
HOST_2A_1 = "host_2a_1"
HOST_2A_2 = "host_2a_2"
HOST_1B_1 = "host_1b_1"
HOST_1B_2 = "host_1b_2"
HOST_2B_1 = "host_2b_1"
HOST_2B_2 = "host_2b_2"
EDGE_A = "edge_router_a"
EDGE_B = "edge_router_b"
CENTRAL = "central_router"

REQUIRED_CONTAINERS = (
    HOST_1A_1,
    HOST_1A_2,
    HOST_2A_1,
    HOST_2A_2,
    HOST_1B_1,
    HOST_1B_2,
    HOST_2B_1,
    HOST_2B_2,
    EDGE_A,
    EDGE_B,
    CENTRAL,
)

# Inventory mirrors config.yml / docker-compose.yml.
IP = {
    HOST_1A_1: "192.168.2.10",
    HOST_1A_2: "192.168.2.11",
    HOST_2A_1: "192.168.1.10",
    HOST_2A_2: "192.168.1.11",
    HOST_1B_1: "192.168.4.10",
    HOST_1B_2: "192.168.4.11",
    HOST_2B_1: "192.168.3.10",
    HOST_2B_2: "192.168.3.11",
    "gw_1a": "192.168.2.1",
    "gw_2a": "192.168.1.1",
    "gw_1b": "192.168.4.1",
    "gw_2b": "192.168.3.1",
    "wan_a_edge": "1.1.1.1",
    "wan_a_central": "1.1.1.2",
    "wan_b_edge": "1.1.2.1",
    "wan_b_central": "1.1.2.2",
    "vti_edge_a": "10.255.10.1",
    "vti_central": "10.255.10.2",
    "vxlan_edge_b": "10.255.20.1",
    "vxlan_central": "10.255.20.2",
    "internet_gw": "203.0.113.254",
}

SAME_SUBNET = (
    (HOST_1A_1, IP[HOST_1A_2]),
    (HOST_1A_2, IP[HOST_1A_1]),
    (HOST_2A_1, IP[HOST_2A_2]),
    (HOST_2A_2, IP[HOST_2A_1]),
    (HOST_1B_1, IP[HOST_1B_2]),
    (HOST_1B_2, IP[HOST_1B_1]),
    (HOST_2B_1, IP[HOST_2B_2]),
    (HOST_2B_2, IP[HOST_2B_1]),
)

INTRA_SITE = (
    (HOST_1A_1, IP[HOST_2A_1]),
    (HOST_2A_1, IP[HOST_1A_1]),
    (HOST_1B_1, IP[HOST_2B_1]),
    (HOST_2B_1, IP[HOST_1B_1]),
)

WAN = (
    (EDGE_A, IP["wan_a_central"]),
    (CENTRAL, IP["wan_a_edge"]),
    (EDGE_B, IP["wan_b_central"]),
    (CENTRAL, IP["wan_b_edge"]),
)

OVERLAY = (
    (EDGE_A, IP["vti_central"]),
    (CENTRAL, IP["vti_edge_a"]),
    (EDGE_B, IP["vxlan_central"]),
    (CENTRAL, IP["vxlan_edge_b"]),
)

SITE_TO_SITE = (
    (HOST_1A_1, IP[HOST_1B_1]),
    (HOST_1B_1, IP[HOST_1A_1]),
    (HOST_2A_1, IP[HOST_2B_1]),
    (HOST_2B_1, IP[HOST_2A_1]),
)

NATED_HOSTS = (HOST_1A_1, HOST_1B_1)
UNNATED_HOSTS = (HOST_2A_1, HOST_2B_1)


def docker_exec(container: str, *args: str, timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "exec", container, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def ping_from(container: str, dst: str) -> subprocess.CompletedProcess:
    return docker_exec(container, "ping", "-c", PING_COUNT, "-W", PING_WAIT, dst)


def format_result(proc: subprocess.CompletedProcess) -> str:
    parts = [f"exit={proc.returncode}"]
    if proc.stdout:
        parts.append(proc.stdout.strip())
    if proc.stderr:
        parts.append(proc.stderr.strip())
    return "\n".join(parts)


def assert_ping(test: unittest.TestCase, src: str, dst: str) -> None:
    proc = ping_from(src, dst)
    test.assertEqual(
        proc.returncode,
        0,
        f"ping {src} -> {dst} failed\n{format_result(proc)}",
    )


def assert_no_ping(test: unittest.TestCase, src: str, dst: str) -> None:
    proc = ping_from(src, dst)
    test.assertNotEqual(
        proc.returncode,
        0,
        f"ping {src} -> {dst} unexpectedly succeeded\n{format_result(proc)}",
    )


class TestLabUp(unittest.TestCase):
    def test_required_containers_running(self) -> None:
        proc = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, format_result(proc))
        running = {name.strip() for name in proc.stdout.splitlines() if name.strip()}
        missing = [name for name in REQUIRED_CONTAINERS if name not in running]
        self.assertFalse(missing, f"containers not running: {missing}")


class TestSameSubnet(unittest.TestCase):
    def test_hosts_ping_lan_peer(self) -> None:
        for src, dst in SAME_SUBNET:
            with self.subTest(src=src, dst=dst):
                assert_ping(self, src, dst)


class TestIntraSite(unittest.TestCase):
    def test_hosts_ping_other_local_subnet(self) -> None:
        for src, dst in INTRA_SITE:
            with self.subTest(src=src, dst=dst):
                assert_ping(self, src, dst)


class TestWan(unittest.TestCase):
    def test_wan_p2p(self) -> None:
        for src, dst in WAN:
            with self.subTest(src=src, dst=dst):
                assert_ping(self, src, dst)


class TestOverlay(unittest.TestCase):
    def test_ipsec_vti_and_vxlan(self) -> None:
        for src, dst in OVERLAY:
            with self.subTest(src=src, dst=dst):
                assert_ping(self, src, dst)


class TestSiteToSite(unittest.TestCase):
    def test_hosts_ping_remote_site(self) -> None:
        for src, dst in SITE_TO_SITE:
            with self.subTest(src=src, dst=dst):
                assert_ping(self, src, dst)


class TestInternetNat(unittest.TestCase):
    def test_central_reaches_internet_gateway(self) -> None:
        assert_ping(self, CENTRAL, IP["internet_gw"])

    def test_natted_subnets_reach_internet(self) -> None:
        for src in NATED_HOSTS:
            with self.subTest(src=src, dst=INTERNET_IP):
                assert_ping(self, src, INTERNET_IP)

    def test_unnated_subnets_blocked(self) -> None:
        for src in UNNATED_HOSTS:
            with self.subTest(src=src, dst=INTERNET_IP):
                assert_no_ping(self, src, INTERNET_IP)


if __name__ == "__main__":
    unittest.main()
