# ⚡ Mini-VPS Manager Suite

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Linux](https://img.shields.io/badge/Platform-Ubuntu%20%7C%20Debian-blue.svg)](https://ubuntu.com)
[![Virtualization: LXD](https://img.shields.io/badge/Engine-LXD%20Containers-green.svg)](https://ubuntu.com/lxd)
[![API: FastAPI](https://img.shields.io/badge/API-FastAPI%20REST-009688.svg)](https://fastapi.tiangolo.com)
[![Author: Mohd Khatab](https://img.shields.io/badge/Author-Mohd%20Khatab-orange.svg)](https://github.com/mohdkhatab)

**Mini-VPS Manager Suite** is an enterprise-grade, zero-overhead virtualization management tool and REST API that allows you to partition any Linux VPS or Dedicated Server into multiple, fully isolated, customizable **Mini-VPS** instances.

Each Mini-VPS behaves exactly like a standalone cloud VPS (DigitalOcean / AWS / Linode instance) with its own **init system (systemd), independent root filesystem, dedicated CPU cores, RAM limits, isolated Btrfs storage quotas, custom SSH port, independent root/sudo credentials, and full REST API control**.

---

## 🌟 Key Highlights / Khasiyatain

* 🚀 **1-Click Zero-Touch Setup:** Complete automated installation in under 60 seconds.
* 🎛️ **100% Customizable Virtualization:**
  * Custom **Instance Name** (e.g. `client1`, `node-2`, `worker`).
  * Custom **CPU Cores Allocation** (1, 2, 4, 8 cores).
  * Custom **RAM Allocation** (1GB, 2GB, 4GB, 8GB, 16GB, etc.).
  * Dedicated **Storage Limit** via Btrfs quotas (10GB, 20GB, 32GB, 50GB, etc.).
  * Custom **External SSH Port** (e.g., 2222, 2223, 2224).
  * Independent **Username & Password** with sudo root access.
  * Multi-OS support: Ubuntu 22.04 LTS, Ubuntu 24.04 LTS, Debian 12, Debian 11, Alpine Linux.
* 🌐 **REST API & Swagger UI:** Control VPS instances programmatically via REST API (`/api/vps/status`, `/exec`, `/start`, `/stop`, `/restart`, `/create`, `/delete`) with interactive Swagger docs at `http://<IP>:8090/docs`.
* 🖥️ **Interactive Terminal TUI Menu:** Beautiful color menu (`minivps menu`) for easy 1-click management.
* 🐳 **Docker Coexistence:** Automatic iptables routing that prevents Docker from blocking LXD bridge traffic.
* 🔄 **Persistent on Boot:** Autostart support for both the containers and the management API service.

---

## ⚡ Quick 1-Line Installation

Run this command on your VPS as `root` or with `sudo`:

```bash
curl -sSL https://raw.githubusercontent.com/mohdkhatab/minivps-manager/main/install.sh | sudo bash
```

Once installed, simply type:
```bash
minivps
```

---

## 🛠️ Interactive Management Menu

Launch the interactive control menu at any time:

```bash
minivps menu
```

```text
=================================================================
                     MINI-VPS MANAGER SUITE                      
           Customizable Virtual Environment & REST API           
-----------------------------------------------------------------
 Host Public IPv4 : 18.118.50.137
 Virtualization   : LXD System Containers (Zero-Overhead)
 REST API Service : Active (Port 8090)
=================================================================
 [1]  Create New Mini-VPS (Custom CPU, RAM, Disk, User, Pass)
 [2]  List All Mini-VPS Instances
 [3]  Mini-VPS Information & SSH Credentials
 [4]  Live Status & Resource Statistics (RAM/CPU/Disk)
 [5]  1-Click Shell Login (Direct Terminal Inside VPS)
-----------------------------------------------------------------
 [6]  Start Mini-VPS
 [7]  Stop Mini-VPS
 [8]  Restart Mini-VPS
 [9]  Change User Password
 [10] Execute Command inside Mini-VPS
-----------------------------------------------------------------
 [11] Show REST API Details & cURL Documentation
 [12] Delete Mini-VPS Instance & Free Storage
 [0]  Exit Menu
=================================================================
```

---

## 💻 CLI Command Reference

You can also run direct CLI commands without entering the menu:

| Command | Description | Example |
| :--- | :--- | :--- |
| `minivps menu` | Open interactive TUI management menu | `minivps menu` |
| `minivps list` | List all active Mini-VPS containers | `minivps list` |
| `minivps create` | Launch interactive wizard to build a VPS | `minivps create` |
| `minivps create <args>` | Non-interactive 1-line creation | `minivps create node1 ubuntu:22.04 2 4 32 2222 admin Pass123!` |
| `minivps info [name]` | Show VPS specs, IP, SSH command & API key | `minivps info minivps` |
| `minivps status [name]` | Live CPU %, RAM MB, Disk GB and Uptime | `minivps status minivps` |
| `minivps shell [name]` | Direct 1-click shell login into the VPS | `minivps shell minivps` |
| `minivps start [name]` | Start a stopped VPS container | `minivps start minivps` |
| `minivps stop [name]` | Stop a running VPS container | `minivps stop minivps` |
| `minivps restart [name]` | Reboot / Restart the Mini-VPS | `minivps restart minivps` |
| `minivps passwd [name] [usr] [pwd]` | Update user or root password | `minivps passwd minivps vpsadmin NewPass!` |
| `minivps exec [name] "<cmd>"` | Execute shell command inside the VPS | `minivps exec minivps "df -h; uptime"` |
| `minivps delete [name]` | Permanently delete container and disk pool | `minivps delete node1` |
| `minivps api` | Print API endpoints and cURL examples | `minivps api` |

---

## 📡 REST API & Integration

Mini-VPS Manager provides a FastAPI service with OpenAPI/Swagger documentation.

* **Base URL:** `http://<YOUR_VPS_IP>:8090`
* **Swagger UI:** `http://<YOUR_VPS_IP>:8090/docs`
* **ReDoc:** `http://<YOUR_VPS_IP>:8090/redoc`
* **Authentication Header:** `X-API-Key: <your_api_key>` (or `?api_key=<your_api_key>`)

### 📋 API Endpoints

#### 1. Live Resource Status (CPU, RAM, Disk, Uptime)
```bash
curl -H "X-API-Key: YOUR_API_KEY" http://YOUR_VPS_IP:8090/api/vps/minivps/status
```
**Response:**
```json
{
  "name": "minivps",
  "status": "RUNNING",
  "is_running": true,
  "uptime": "up 15 minutes",
  "memory": {
    "total_mb": 4096,
    "used_mb": 75,
    "free_mb": 3560,
    "usage_percent": 1.8
  },
  "disk": {
    "total": "32G",
    "used": "1.4G",
    "available": "31G",
    "usage_percent": "5%"
  },
  "internal_ips": [
    "10.132.53.210"
  ]
}
```

#### 2. Execute Shell Command via API
```bash
curl -X POST -H "X-API-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"command": "uname -a; uptime"}' \
     http://YOUR_VPS_IP:8090/api/vps/minivps/exec
```

#### 3. Restart Mini-VPS
```bash
curl -X POST -H "X-API-Key: YOUR_API_KEY" http://YOUR_VPS_IP:8090/api/vps/minivps/restart
```

#### 4. Create New Mini-VPS via API
```bash
curl -X POST -H "X-API-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "worker1",
       "os_image": "ubuntu:22.04",
       "cpu": 2,
       "ram_gb": 4,
       "storage_gb": 32,
       "ssh_port": 2225,
       "username": "clientuser",
       "password": "SecurePassword123!"
     }' \
     http://YOUR_VPS_IP:8090/api/vps/create
```

#### 5. Change Password via API
```bash
curl -X POST -H "X-API-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"username": "vpsadmin", "password": "NewStrongPassword456!"}' \
     http://YOUR_VPS_IP:8090/api/vps/minivps/user/password
```

---

## 🔒 Security & Firewall

Ensure the following ports are open in your Cloud Provider's Security Group (AWS, Hetzner, DigitalOcean, Oracle Cloud, etc.):
* **Host SSH:** `22` (TCP)
* **Mini-VPS SSH:** `2222` (TCP) (or whichever port you configured)
* **REST API:** `8090` (TCP)

To configure `ufw` locally:
```bash
sudo ufw allow 2222/tcp
sudo ufw allow 8090/tcp
```

---

## 🗑️ Uninstallation

To remove Mini-VPS Manager and cleanly revert system services:
```bash
sudo /home/ubuntu/minivps-manager/uninstall.sh
```

---

## 👤 Author & Support
* **Developer:** Mohd Khatab
* **Email:** mrkhatab112@gmail.com
* **GitHub:** [@mohdkhatab](https://github.com/mohdkhatab)
* **License:** [MIT License](LICENSE)
