# 📖 Mini-VPS Manager - Command Reference Guide

This document contains full details for all available CLI commands, options, and REST API parameters.

---

## 1. CLI Usage

The CLI binary is installed at `/usr/local/bin/minivps` and symlinked to `/usr/local/bin/mvps`.

### `minivps menu`
Launches the interactive Terminal User Interface (TUI) with colored options.

### `minivps list` (or `minivps ls`)
Displays a formatted table of all containers, their IPv4/IPv6 addresses, type, and current state.

### `minivps create [name] [os] [cpu] [ram] [disk] [port] [user] [pass]`
Creates a new isolated container instance.
* If arguments are omitted, launches the step-by-step interactive configuration wizard.
* If arguments are provided, performs non-interactive 1-shot provisioning:
  ```bash
  minivps create node1 ubuntu:22.04 2 4 32 2222 vpsadmin "MySecretPass#123"
  ```
  **Parameters:**
  1. `name`: Unique instance label (e.g. `client-vps`)
  2. `os`: Container image (`ubuntu:22.04`, `ubuntu:24.04`, `images:debian/12`, `images:alpine/3.19`)
  3. `cpu`: Number of vCPUs to allocate
  4. `ram`: RAM allocation in Gigabytes
  5. `disk`: Storage pool quota in Gigabytes
  6. `port`: External host port mapped to container port 22
  7. `user`: Initial administrative username
  8. `pass`: User and root password

### `minivps info [name]`
Displays configuration metadata, connection string, specifications, API endpoints, and authentication tokens.

### `minivps status [name]`
Queries container resource metrics:
* Memory (Total MB, Used MB, Free MB, Usage %)
* Disk (Total Size, Used Size, Available Size, Usage %)
* Uptime
* Internal Bridge IPs

### `minivps shell [name]` (or `ssh`, `login`)
Directly attaches an interactive bash session into the container as the configured admin user.

### `minivps start [name]`
Starts the container instance.

### `minivps stop [name]`
Gracefully powers down the container instance.

### `minivps restart [name]` (or `reboot`)
Reboots the container instance.

### `minivps passwd [name] [user] [new_password]`
Changes the password for any local user or root inside the target container.

### `minivps exec [name] "<command>"`
Runs an arbitrary shell command non-interactively and outputs the result.
```bash
minivps exec minivps "apt-get update && apt-get install -y nginx"
```

### `minivps delete [name]` (or `rm`, `destroy`)
Prompts for confirmation, stops the container, deletes it, and reclaims the dedicated Btrfs storage pool.

### `minivps api`
Displays the active REST API URL, secret token, and copy-pasteable cURL snippets.

---

## 2. REST API Reference

The REST API service runs via `minivps-api.service` on port `8090` by default.

### Authentication
Include the `X-API-Key` header with each request:
```http
X-API-Key: mvps_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
Or append as a query parameter:
```http
?api_key=mvps_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Endpoints Table

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Service health status and documentation links |
| `GET` | `/docs` | Interactive Swagger UI (OpenAPI) |
| `GET` | `/redoc` | Interactive ReDoc documentation |
| `GET` | `/api/vps/list` | List all managed instances and live statuses |
| `GET` | `/api/vps/{name}/info` | Specifications, ports, and connection string |
| `GET` | `/api/vps/{name}/status` | Live CPU, RAM, Disk, Uptime, IPs |
| `POST` | `/api/vps/{name}/start` | Start instance |
| `POST` | `/api/vps/{name}/stop` | Stop instance |
| `POST` | `/api/vps/{name}/restart` | Reboot instance |
| `POST` | `/api/vps/{name}/exec` | Execute shell command inside container |
| `POST` | `/api/vps/{name}/user/password` | Update password for an existing user |
| `POST` | `/api/vps/{name}/user/create` | Create a new user with optional sudo |
| `POST` | `/api/vps/create` | Provision a new Mini-VPS instance dynamically |
| `DELETE`| `/api/vps/{name}` | Destroy instance and free storage pool |
