interfaces {
    ethernet eth0 {
        address "1.1.2.1/30"
        description "WAN-to-Central"
    }
    ethernet eth1 {
        address "192.168.4.1/24"
        description "Subnet1B"
    }
    ethernet eth2 {
        address "192.168.3.1/24"
        description "Subnet2B"
    }
    ethernet eth3 {
        address "10.0.0.3/24"
        description "Mgmt-API"
    }
    loopback lo {
    }
}
service {
    https {
        api {
            keys {
                id provisioner {
                    key "lab-api-key"
                }
            }
        }
        listen-address "0.0.0.0"
    }
    ssh {
        port "22"
    }
}
system {
    config-management {
        commit-revisions "200"
    }
    host-name "edge-router-b"
    login {
        user vyos {
            authentication {
                encrypted-password "$6$QxPS.uk6mfo$9QBSo8u1FkH16gMyAVhus6fU3LOzvLR9Z9.82m3tiHFAxTtIkhaZSWssSgzt4v4dGAL8rhVQxTg0oAG9/q11h/"
                plaintext-password ""
            }
        }
    }
    syslog {
        global {
            facility all {
                level "info"
            }
            facility protocols {
                level "debug"
            }
        }
    }
}

// Warning: Do not remove the following line.
// vyos-config-version: "bgp@1:broadcast-relay@1:cluster@1:config-management@1:conntrack@2:conntrack-sync@2:dhcp-relay@2:dhcp-server@5:dhcpv6-server@1:dns-forwarding@3:firewall@5:https@2:interfaces@20:ipoe-server@1:isis@1:l2tp@3:lldp@1:mdns@1:nat@5:nat66@1:ntp@1:pppoe-server@5:pptp@2:qos@1:quagga@9:rpki@1:salt@1:snmp@2:ssh@2:sstp@3:system@21:vrf@2:vrrp@2:vyos-accel-ppp@2:wanloadbalance@3:webproxy@2:zone-policy@1"
// Release version: 1.4-rolling-202106011750
