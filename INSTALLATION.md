# 📦 Mini-VPS Manager - Installation & Setup Guide

This guide covers system prerequisites, installation methods, systemd integration, and troubleshooting.

---

## 1. System Requirements

* **Operating System:**
  * Ubuntu 20.04 LTS / 22.04 LTS / 24.04 LTS
  * Debian 11 (Bullseye) / Debian 12 (Bookworm)
* **Access Level:** Root or user with full `sudo` privileges
* **Architecture:** `x86_64` (AMD64) or `aarch64` (ARM64)
* **Minimum Host Resources:**
  * 1 vCPU
  * 1 GB RAM (Free memory)
  * 10 GB Disk space (Free disk space)

---

## 2. Automated Installation (Recommended)

Run the single-line installer directly in your terminal:

```bash
curl -sSL https://raw.githubusercontent.com/mohdkhatab/minivps-manager/main/install.sh | sudo bash
```

The installer will automatically:
1. Detect system architecture and packages.
2. Install `btrfs-progs`, `jq`, `curl`, `python3`, `iptables`.
3. Set up LXD and configure the storage engine.
4. Establish non-conflicting bridge routes compatible with Docker.
5. Deploy `minivps-api.service` on port `8090`.
6. Install the `minivps` CLI into `/usr/local/bin/minivps`.

---

## 3. Manual Installation (Step-by-Step)

If you prefer to install manually:

```bash
# 1. Clone the repository
git clone https://github.com/mohdkhatab/minivps-manager.git /opt/minivps-manager
cd /opt/minivps-manager

# 2. Install dependencies
sudo apt-get update
sudo apt-get install -y curl wget jq btrfs-progs python3 python3-pip python3-fastapi python3-uvicorn iptables

# 3. Initialize LXD
sudo lxd init --auto

# 4. Copy CLI binary
sudo cp bin/minivps /usr/local/bin/minivps
sudo chmod +x /usr/local/bin/minivps
sudo ln -sf /usr/local/bin/minivps /usr/local/bin/mvps

# 5. Set up API service
sudo mkdir -p /opt/minivps-api /etc/minivps
sudo cp api/main.py /opt/minivps-api/main.py
sudo cp systemd/minivps-api.service /etc/systemd/system/minivps-api.service
sudo cp systemd/minivps-iptables.service /etc/systemd/system/minivps-iptables.service

# 6. Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable --now minivps-iptables.service
sudo systemctl enable --now minivps-api.service
```

---

## 4. Verification & Diagnostics

After installation, verify that all components are operational:

```bash
# Verify CLI
minivps info

# Verify API Service
systemctl status minivps-api.service

# Test API endpoint
curl -s http://127.0.0.1:8090/ | jq .
```

---

## 5. Troubleshooting

### Issue: Mini-VPS has no internet access inside container
If you have Docker installed on the same server, Docker sets the default iptables `FORWARD` policy to `DROP`.
Mini-VPS Manager automatically handles this with `minivps-iptables.service`. To manually enforce:
```bash
sudo iptables -I DOCKER-USER -i lxdbr0 -j ACCEPT
sudo iptables -I DOCKER-USER -o lxdbr0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
sudo iptables -I FORWARD -i lxdbr0 -j ACCEPT
```

### Issue: Cannot connect via external SSH port
Ensure your cloud firewall (AWS Security Group, DigitalOcean Firewall, Hetzner Firewall) allows inbound traffic on the custom SSH port (e.g. `2222/tcp`) and the API port (`8090/tcp`).
