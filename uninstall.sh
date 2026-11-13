#!/usr/bin/env bash
# ==============================================================================
#                 MINI-VPS MANAGER - UNINSTALLER SCRIPT
# ==============================================================================

set -e

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[Error] Please run this uninstaller as root or with sudo.${NC}"
    exit 1
fi

echo -e "${RED}=================================================================${NC}"
echo -e "${RED}             UNINSTALL MINI-VPS MANAGER SUITE                    ${NC}"
echo -e "${RED}=================================================================${NC}"
read -rp "Are you sure you want to uninstall Mini-VPS Manager? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

read -rp "Do you also want to remove all created Mini-VPS containers & storage? (y/N): " rm_all

echo -e "${YELLOW}[*] Stopping and disabling systemd services...${NC}"
systemctl stop minivps-api.service 2>/dev/null || true
systemctl disable minivps-api.service 2>/dev/null || true
rm -f /etc/systemd/system/minivps-api.service /etc/systemd/system/minivps-iptables.service
systemctl daemon-reload

echo -e "${YELLOW}[*] Removing binaries and API code...${NC}"
rm -f /usr/local/bin/minivps /usr/local/bin/mvps
rm -rf /opt/minivps-api

if [[ "$rm_all" =~ ^[Yy]$ ]]; then
    echo -e "${RED}[*] Deleting all Mini-VPS instances and storage pools...${NC}"
    for c in $(lxc list -c n --format csv 2>/dev/null); do
        echo "Deleting container: $c"
        lxc stop "$c" --force 2>/dev/null || true
        lxc delete "$c" 2>/dev/null || true
    done
    rm -rf /etc/minivps
else
    echo -e "${GREEN}[*] Keeping container data and /etc/minivps/config.json intact.${NC}"
fi

echo -e "${GREEN}[✓] Mini-VPS Manager uninstalled successfully.${NC}"
