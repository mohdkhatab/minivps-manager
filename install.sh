#!/usr/bin/env bash
# ==============================================================================
#           MINI-VPS MANAGER - 1-CLICK AUTOMATED INSTALLER
#       Transforms any Linux VPS into a Multi-VPS Virtualization Host
# ==============================================================================

set -e

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
CYAN='\033[1;36m'
MAGENTA='\033[1;35m'
BOLD='\033[1m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[Error] Please run this installer as root or with sudo.${NC}"
    exit 1
fi

echo -e "${CYAN}=================================================================${NC}"
echo -e "${GREEN}${BOLD}             MINI-VPS MANAGER: 1-CLICK INSTALLER                 ${NC}"
echo -e "${YELLOW}       High-Performance System Containers & Cloud REST API       ${NC}"
echo -e "${CYAN}=================================================================${NC}"

# 1. Update and install basic dependencies
echo -e "${YELLOW}[1/6] Installing core dependencies (curl, jq, btrfs, python3)...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y >/dev/null 2>&1 || true
apt-get install -y curl wget jq btrfs-progs python3 python3-pip python3-fastapi python3-uvicorn iptables openssh-client >/dev/null 2>&1 || {
    echo -e "${YELLOW}[!] Installing python packages via pip fallback...${NC}"
    apt-get install -y curl wget jq btrfs-progs python3 python3-pip iptables openssh-client
    pip3 install fastapi "uvicorn[standard]" pydantic --break-system-packages 2>/dev/null || pip3 install fastapi "uvicorn[standard]" pydantic 2>/dev/null || true
}

# 2. Check and install LXD
echo -e "${YELLOW}[2/6] Checking and configuring LXD Virtualization Engine...${NC}"
if ! command -v lxd >/dev/null 2>&1; then
    echo -e "${YELLOW}[*] Installing LXD via Snap...${NC}"
    snap install lxd || apt-get install -y lxd
fi

# Initialize LXD if not initialized
if ! lxc storage list >/dev/null 2>&1; then
    echo -e "${YELLOW}[*] Initializing LXD default networking and bridge...${NC}"
    lxd init --auto
fi

# 3. Configure iptables forwarding (fixes Docker conflict)
echo -e "${YELLOW}[3/6] Configuring network bridge & Docker compatibility...${NC}"
iptables -I DOCKER-USER -i lxdbr0 -j ACCEPT 2>/dev/null || true
iptables -I DOCKER-USER -o lxdbr0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
iptables -I FORWARD -i lxdbr0 -j ACCEPT 2>/dev/null || true
iptables -I FORWARD -o lxdbr0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true

# Install persistent iptables service
cat << 'NET_EOF' > /etc/systemd/system/minivps-iptables.service
[Unit]
Description=Ensure LXD Bridge Forwarding with Docker
After=docker.service lxd.service
Wants=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/sbin/iptables -I DOCKER-USER -i lxdbr0 -j ACCEPT
ExecStart=/sbin/iptables -I DOCKER-USER -o lxdbr0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
ExecStart=/sbin/iptables -I FORWARD -i lxdbr0 -j ACCEPT
ExecStart=/sbin/iptables -I FORWARD -o lxdbr0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

[Install]
WantedBy=multi-user.target
NET_EOF
systemctl daemon-reload
systemctl enable minivps-iptables.service >/dev/null 2>&1 || true

# 4. Install REST API service
echo -e "${YELLOW}[4/6] Installing Mini-VPS REST API Service...${NC}"
mkdir -p /opt/minivps-api /etc/minivps

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/api/main.py" ]; then
    cp "$SCRIPT_DIR/api/main.py" /opt/minivps-api/main.py
else
    curl -sSL https://raw.githubusercontent.com/mohdkhatab/minivps-manager/main/api/main.py -o /opt/minivps-api/main.py
fi

# Generate config and API key if not exists
python3 -c "
import json, secrets, os, urllib.request
cfg_path = '/etc/minivps/config.json'
if not os.path.exists(cfg_path):
    try:
        pub_ip = urllib.request.urlopen('https://api.ipify.org', timeout=3).read().decode().strip()
    except Exception:
        pub_ip = '127.0.0.1'
    data = {
        'api_key': 'mvps_' + secrets.token_hex(16),
        'api_port': 8090,
        'public_ip': pub_ip,
        'default_instance': 'minivps',
        'instances': {}
    }
    with open(cfg_path, 'w') as f:
        json.dump(data, f, indent=2)
os.chmod(cfg_path, 0o644)
"

# Install API systemd service
cat << 'API_EOF' > /etc/systemd/system/minivps-api.service
[Unit]
Description=Mini VPS Management REST API Service
After=network.target lxd.service
Wants=lxd.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/minivps-api
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8090
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
API_EOF
systemctl daemon-reload
systemctl enable --now minivps-api.service >/dev/null 2>&1 || true

# 5. Install CLI tool
echo -e "${YELLOW}[5/6] Installing 'minivps' CLI binary to /usr/local/bin...${NC}"
if [ -f "$SCRIPT_DIR/bin/minivps" ]; then
    cp "$SCRIPT_DIR/bin/minivps" /usr/local/bin/minivps
else
    curl -sSL https://raw.githubusercontent.com/mohdkhatab/minivps-manager/main/bin/minivps -o /usr/local/bin/minivps
fi
chmod +x /usr/local/bin/minivps
ln -sf /usr/local/bin/minivps /usr/local/bin/mvps

# 6. Interactive Setup or Summary
echo -e "${YELLOW}[6/6] Finalizing installation...${NC}"
PUB_IP=$(python3 -c "import json; print(json.load(open('/etc/minivps/config.json')).get('public_ip', '127.0.0.1'))" 2>/dev/null || echo "127.0.0.1")
API_KEY=$(python3 -c "import json; print(json.load(open('/etc/minivps/config.json')).get('api_key', ''))" 2>/dev/null || echo "")

echo ""
echo -e "${GREEN}=================================================================${NC}"
echo -e "${GREEN}${BOLD}         [✓] MINI-VPS MANAGER INSTALLED SUCCESSFULLY!            ${NC}"
echo -e "${GREEN}=================================================================${NC}"
echo -e " ${YELLOW}Host Public IP :${NC} $PUB_IP"
echo -e " ${YELLOW}REST API URL   :${NC} http://$PUB_IP:8090"
echo -e " ${YELLOW}Swagger Docs   :${NC} http://$PUB_IP:8090/docs"
echo -e " ${YELLOW}API Secret Key :${NC} ${GREEN}$API_KEY${NC}"
echo -e "${CYAN}-----------------------------------------------------------------${NC}"
echo -e " ${MAGENTA}CLI Commands:${NC}"
echo -e "   ${GREEN}minivps menu${NC}       - Open Interactive Management TUI"
echo -e "   ${GREEN}minivps create${NC}     - Create a new custom Mini-VPS"
echo -e "   ${GREEN}minivps list${NC}       - List all active instances"
echo -e "   ${GREEN}minivps info${NC}       - Show specs, SSH port and credentials"
echo -e "   ${GREEN}minivps status${NC}     - Live CPU, RAM, and Disk metrics"
echo -e "   ${GREEN}minivps shell${NC}      - 1-click shell login into VPS"
echo -e "   ${GREEN}minivps api${NC}        - View API cURL documentation"
echo -e "${GREEN}=================================================================${NC}"
echo ""
echo -e "Type ${GREEN}minivps${NC} or ${GREEN}mvps${NC} anytime to manage your instances!"
