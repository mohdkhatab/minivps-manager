# ⚡ Prime Khatab Mini-VPS Enterprise Manager

<p align="center">
  <b>Built with ❤️ by Prime Khatab</b><br>
  <i>All-in-One Zero-Overhead Virtualization, Bandwidth Quotas & Expiry Lifecycle Suite</i>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://ubuntu.com"><img src="https://img.shields.io/badge/Platform-Ubuntu%20%7C%20Debian-blue.svg" alt="Platform"></a>
  <a href="https://ubuntu.com/lxd"><img src="https://img.shields.io/badge/Engine-LXD%20Containers-green.svg" alt="Engine"></a>
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/API-FastAPI%20REST%20v2.1-009688.svg" alt="API"></a>
  <a href="https://github.com/mohdkhatab"><img src="https://img.shields.io/badge/Developer-Prime%20Khatab%20%E2%9D%A4%EF%B8%8F-ff69b4.svg" alt="Developer"></a>
</p>

---

## 🚀 Overview

**Prime Khatab Mini-VPS Manager** is a high-performance Linux virtualization management platform and REST API suite developed by **Prime Khatab**. It allows administrators and users to partition any Linux VPS or Dedicated Server into multiple, fully isolated, production-ready **Mini-VPS** environments.

Each Mini-VPS operates with **its own dedicated CPU cores, RAM limits, isolated Btrfs storage quotas, custom SSH port, independent root/sudo credentials, bandwidth traffic monitoring, bandwidth rate limits, automatic expiration lifecycle, and complete REST API control**.

---

## ✨ Key Features

* 💎 **Branded for Excellence:** Built with ❤️ by Prime Khatab.
* ⚡ **Zero-Touch 1-Click Install:** 100% automated installation with single command.
* 📊 **Real-Time Bandwidth Engine:**
  * Tracks exact Bytes received (RX), sent (TX), and total data transfer consumed.
  * Real-time metrics in MB and GB with persistent cumulative counter across restarts.
  * **Bandwidth Quotas:** Admin can set total data transfer limits (e.g. 50GB, 100GB, 500GB).
  * **Speed Rate Limits:** Admin can throttle network speed (e.g. 50Mbit, 100Mbit).
  * **Automatic Suspension:** Suspends instances that exceed their bandwidth quota.
* ⏳ **Duration & Expiry Lifecycle Engine:**
  * Set active lifespan in days (e.g., 7 days, 30 days, 90 days, or unlimited).
  * Auto-tracks creation date, expiration timestamp, and days remaining.
  * **Renewal System:** Renew / extend duration with a single command (`pk renew <name> <days>`).
  * **Auto-Cleaner:** Automatic background timer checks and suspends/prunes expired instances every 10 minutes.
* 🎛️ **Full Customization on Creation:**
  * Custom instance name
  * OS distribution (Ubuntu 22.04 LTS, Ubuntu 24.04 LTS, Debian 12, Debian 11, Alpine Linux 3.19)
  * CPU cores allocation
  * RAM limits (1GB, 2GB, 4GB, 8GB, etc.)
  * Storage quota via dedicated Btrfs loop pools (10GB, 20GB, 32GB, 50GB, etc.)
  * Custom external SSH port (e.g. 2222, 2223, 2224)
  * Custom admin username and password with full password-less sudo
* ⌨️ **Instant Short Commands:** Run `pk`, `vps`, `mvps`, or `minivps` anywhere in your terminal.
* 🌐 **REST API with OpenAPI / Swagger UI:** Full programmatic control at `http://<IP>:8090/docs`.
* 🐳 **Docker Coexistence:** Automatic iptables routing prevents Docker from blocking LXD bridge traffic.

---

## ⚡ 1-Click Automated Setup

Run this single command on your VPS as `root` or with `sudo`:

```bash
curl -sSL https://raw.githubusercontent.com/mohdkhatab/minivps-manager/main/install.sh | sudo bash
```

Once installed, simply type any of the short commands:
```bash
pk
# ya
vps
# ya
mvps
# ya
minivps
```

---

## 🖥️ Interactive TUI Control Menu (`pk` / `vps`)

```text
=================================================================
                     PRIME KHATAB SERVICES                       
               Mini-VPS Virtualization & Cloud Manager           
                    Built with ❤️ by Prime Khatab                 
-----------------------------------------------------------------
 Host Public IPv4 : 18.118.50.137
 Virtualization   : LXD Zero-Overhead System Containers
 REST API Daemon  : Active (Port 8090)
=================================================================
 [1]  Create New Mini-VPS (Custom Specs, Bandwidth Quota, Lifespan)
 [2]  List All Mini-VPS Instances (Live Bandwidth & Expiry)
 [3]  Mini-VPS Information & Credentials
 [4]  Live Status & Resource Statistics (RAM/CPU/Disk/Bandwidth)
 [5]  1-Click Shell Login (Direct Terminal Inside VPS)
-----------------------------------------------------------------
 [6]  Start Mini-VPS
 [7]  Stop Mini-VPS
 [8]  Restart Mini-VPS
 [9]  Renew / Extend Mini-VPS Duration (Add Days)
 [10] Set / Change Bandwidth Quota & Speed Limit
-----------------------------------------------------------------
 [11] Change User Password
 [12] Execute Command inside Mini-VPS
 [13] Auto-Clean Expired Instances (Scan / Suspend / Prune)
 [14] Delete Mini-VPS Instance & Free Storage
 [15] Show REST API Details & cURL Documentation
 [0]  Exit Menu
=================================================================
 Prime Khatab Services • Built with ❤️ by Prime Khatab
=================================================================
```

---

## ⌨️ CLI Command Cheat Sheet

| Short Command | Full Command | Description | Example |
| :--- | :--- | :--- | :--- |
| `pk` / `vps` | `minivps menu` | Launch Interactive TUI Menu | `pk` |
| `pk list` | `minivps list` | List all instances with Bandwidth & Expiry | `pk list` |
| `pk create` | `minivps create` | Interactive creation wizard | `pk create` |
| `pk info <name>` | `minivps info <name>` | Show full specs, bandwidth usage & credentials | `pk info minivps` |
| `pk status <name>` | `minivps status <name>` | Live CPU, RAM, Disk, Uptime & Bandwidth stats | `pk status minivps` |
| `pk renew <name> <days>` | `minivps renew <name> <days>` | Extend lifespan duration by X days | `pk renew minivps 30` |
| `pk limit <name> <gb> [spd]` | `minivps limit` | Set Bandwidth Quota and Speed rate limit | `pk limit minivps 200 50Mbit` |
| `pk shell <name>` | `minivps shell <name>` | 1-Click instant terminal shell inside VPS | `pk shell minivps` |
| `pk start <name>` | `minivps start <name>` | Start instance | `pk start minivps` |
| `pk stop <name>` | `minivps stop <name>` | Stop instance | `pk stop minivps` |
| `pk restart <name>` | `minivps restart <name>` | Reboot / Restart instance | `pk restart minivps` |
| `pk passwd <name> <usr> <pwd>` | `minivps passwd` | Change user or root password | `pk passwd minivps vpsadmin NewPass123` |
| `pk exec <name> "<cmd>"` | `minivps exec` | Execute shell command inside VPS | `pk exec minivps "free -h"` |
| `pk auto-clean` | `minivps auto-clean` | Scan and suspend expired instances | `pk auto-clean` |
| `pk delete <name>` | `minivps delete <name>` | Destroy instance and free Btrfs storage | `pk delete node1` |
| `pk api` | `minivps api` | View REST API endpoints and cURL snippets | `pk api` |

---

## 🌐 REST API Reference

The REST API service runs on port `8090` by default.

* **Base URL:** `http://<YOUR_VPS_IP>:8090`
* **Interactive Swagger UI:** `http://<YOUR_VPS_IP>:8090/docs`
* **Authentication Header:** `X-API-Key: <your_api_key>` (or `?api_key=<your_api_key>`)

### 📋 API Endpoints

#### 1. List Instances with Bandwidth & Expiry
```bash
curl -H "X-API-Key: YOUR_API_KEY" http://YOUR_VPS_IP:8090/api/vps/list
```

#### 2. Detailed Info & Specs
```bash
curl -H "X-API-Key: YOUR_API_KEY" http://YOUR_VPS_IP:8090/api/vps/minivps/info
```

#### 3. Renew / Extend Lifespan
```bash
curl -X POST -H "X-API-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"days": 30}' \
     http://YOUR_VPS_IP:8090/api/vps/minivps/renew
```

#### 4. Update Bandwidth Quota & Speed
```bash
curl -X POST -H "X-API-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"bandwidth_limit_gb": 150, "speed_limit": "50Mbit"}' \
     http://YOUR_VPS_IP:8090/api/vps/minivps/limit
```

#### 5. Provision New Mini-VPS via API
```bash
curl -X POST -H "X-API-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "client-node",
       "os_image": "ubuntu:22.04",
       "cpu": 2,
       "ram_gb": 4,
       "storage_gb": 32,
       "ssh_port": 2223,
       "username": "clientuser",
       "password": "SecurePassword123!",
       "duration_days": 30,
       "bandwidth_limit_gb": 100,
       "speed_limit": "100Mbit"
     }' \
     http://YOUR_VPS_IP:8090/api/vps/create
```

---

## 🔒 Security & Firewall

Open the following ports in your cloud firewall:
* **Host SSH:** `22` (TCP)
* **Mini-VPS SSH:** `2222` (TCP) (or any custom port configured)
* **REST API:** `8090` (TCP)

```bash
sudo ufw allow 2222/tcp
sudo ufw allow 8090/tcp
```

---

## 👑 Author & Credits

* **Brand:** Prime Khatab Services
* **Developer:** Prime Khatab (Mohd Khatab)
* **Email:** mrkhatab112@gmail.com
* **GitHub:** [@mohdkhatab](https://github.com/mohdkhatab)
* **Repository:** [https://github.com/mohdkhatab/minivps-manager](https://github.com/mohdkhatab/minivps-manager)
* **License:** [MIT License](LICENSE)

<p align="center">
  <b>Built with ❤️ by Prime Khatab</b>
</p>
