#!/usr/bin/env bash
# SW-7 wired link between the Pi 4 (camera, telemetry bridge) and the Pi 5
# (dashboard): a NetworkManager profile named sw7-link on eth0 with a fixed
# address on a private subnet and no gateway, so Wi-Fi keeps the default
# route for internet. See DashboardIntegration/TELEMETRY_LINK.md 4.1.
#
#   sudo bash setup_sw7_link.sh pi4     # Pi 4: 10.20.0.1/24
#   sudo bash setup_sw7_link.sh pi5     # Pi 5: 10.20.0.2/24
#
# Safe to run again: the profile is created once and then only updated.
# If the cable is not plugged in yet, the profile is still saved and
# NetworkManager brings it up when the cable is connected.
set -u

usage() {
    echo "usage: sudo $0 pi4|pi5" >&2
    exit 2
}

[ "$#" -eq 1 ] || usage
case "$1" in
    pi4) ADDR=10.20.0.1/24; PEER=10.20.0.2 ;;
    pi5) ADDR=10.20.0.2/24; PEER=10.20.0.1 ;;
    *) usage ;;
esac

CON=sw7-link
IFACE=eth0

if [ "$(id -u)" -ne 0 ]; then
    echo "Run with sudo: sudo $0 $1" >&2
    exit 1
fi
if ! command -v nmcli >/dev/null 2>&1; then
    echo "nmcli not found: this needs NetworkManager (the default on Pi OS trixie)." >&2
    exit 1
fi
if ! ip link show "$IFACE" >/dev/null 2>&1; then
    echo "No interface $IFACE on this machine." >&2
    exit 1
fi

if nmcli -t -f NAME connection show | grep -qx "$CON"; then
    echo "Updating existing profile $CON"
else
    echo "Creating profile $CON"
    nmcli connection add type ethernet ifname "$IFACE" con-name "$CON" || exit 1
fi

# The autoconnect priority makes NetworkManager prefer this profile over
# the default DHCP "Wired connection 1" on eth0.
nmcli connection modify "$CON" \
    connection.interface-name "$IFACE" \
    connection.autoconnect yes \
    connection.autoconnect-priority 50 \
    ipv4.method manual \
    ipv4.addresses "$ADDR" \
    ipv4.gateway "" \
    ipv4.dns "" \
    ipv4.never-default yes \
    ipv4.ignore-auto-dns yes \
    ipv6.method disabled || exit 1

CARRIER=$(cat "/sys/class/net/$IFACE/carrier" 2>/dev/null || echo 0)
if [ "$CARRIER" = "1" ]; then
    if ! nmcli connection up "$CON"; then
        echo "WARNING: could not bring $CON up now; it is saved and will retry on reconnect." >&2
    fi
else
    echo "No cable on $IFACE yet: $CON is saved and comes up when the cable is plugged in."
fi

echo
echo "Profile $CON:"
nmcli -f connection.id,connection.interface-name,connection.autoconnect,connection.autoconnect-priority,ipv4.method,ipv4.addresses,ipv4.gateway,ipv4.never-default,ipv6.method \
    connection show "$CON"
echo
echo "Addresses on $IFACE:"
ip -4 -br addr show "$IFACE"
echo
echo "Default route (should still be Wi-Fi):"
ip route show default
echo
echo "When both Pis are set up and cabled, check with: ping -c 3 $PEER"
