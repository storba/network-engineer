interfaces {
    ethernet eth0 {
        address 203.0.113.1/24
        description INTERNET
    }
    ethernet eth1 {
        address 10.0.0.1/24
        description Mgmt-API
    }
    ethernet eth2 {
        address 1.1.1.2/30
        description WAN-to-SiteA
    }
    ethernet eth3 {
        address 1.1.2.2/30
        description WAN-to-SiteB
    }
    loopback lo {
    }
    vti vti0 {
        address 10.255.10.2/30
    }
    vxlan vxlan0 {
        address 10.255.20.2/24
        port 4789
        remote 1.1.2.1
        source-address 1.1.2.2
        vni 100
    }
}
nat {
    source {
        rule 10 {
            outbound-interface eth0
            source {
                address 192.168.2.0/24
            }
            translation {
                address masquerade
            }
        }
        rule 11 {
            outbound-interface eth0
            source {
                address 192.168.4.0/24
            }
            translation {
                address masquerade
            }
        }
    }
}
protocols {
    static {
        route 0.0.0.0/0 {
            next-hop 203.0.113.254 {
            }
        }
        route 192.168.1.0/24 {
            next-hop 10.255.10.1 {
            }
        }
        route 192.168.2.0/24 {
            next-hop 10.255.10.1 {
            }
        }
        route 192.168.3.0/24 {
            next-hop 10.255.20.1 {
            }
        }
        route 192.168.4.0/24 {
            next-hop 10.255.20.1 {
            }
        }
    }
}
service {
    https {
        api {
            keys {
                id provisioner {
                    key lab-api-key
                }
            }
        }
    }
    ssh {
        port 22
    }
}
system {
    config-management {
        commit-revisions 200
    }
    host-name central-router
    login {
        user vyos {
            authentication {
                encrypted-password $6$QxPS.uk6mfo$9QBSo8u1FkH16gMyAVhus6fU3LOzvLR9Z9.82m3tiHFAxTtIkhaZSWssSgzt4v4dGAL8rhVQxTg0oAG9/q11h/
                plaintext-password ""
            }
        }
    }
    syslog {
        global {
            facility all {
                level info
            }
            facility protocols {
                level debug
            }
        }
    }
}
vpn {
    ipsec {
        esp-group ESP-LAB {
            lifetime 1800
            pfs dh-group14
            proposal 1 {
                encryption aes256
                hash sha256
            }
        }
        ike-group IKE-LAB {
            key-exchange ikev2
            lifetime 3600
            proposal 1 {
                dh-group 14
                encryption aes256
                hash sha256
            }
        }
        ipsec-interfaces {
            interface eth2
        }
        options {
            disable-route-autoinstall
        }
        site-to-site {
            peer 1.1.1.1 {
                authentication {
                    mode pre-shared-secret
                    pre-shared-secret lab-ipsec-psk
                }
                ike-group IKE-LAB
                local-address 1.1.1.2
                vti {
                    bind vti0
                    esp-group ESP-LAB
                }
            }
        }
    }
}


// Warning: Do not remove the following line.
// vyos-config-version: "bgp@1:broadcast-relay@1:cluster@1:config-management@1:conntrack@2:conntrack-sync@2:dhcp-relay@2:dhcp-server@5:dhcpv6-server@1:dns-forwarding@3:firewall@5:https@2:interfaces@20:ipoe-server@1:isis@1:l2tp@3:lldp@1:mdns@1:nat@5:nat66@1:ntp@1:pppoe-server@5:pptp@2:qos@1:quagga@9:rpki@1:salt@1:snmp@2:ssh@2:sstp@3:system@21:vrf@2:vrrp@2:vyos-accel-ppp@2:wanloadbalance@3:webproxy@2:zone-policy@1"
// Release version: 1.4-rolling-202106011750
