import os
import json
import secrets
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from pydantic import BaseModel, Field

CONFIG_PATH = "/etc/minivps/config.json"

def load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_PATH):
        return {
            "api_key": "mvps_" + secrets.token_hex(16),
            "api_port": 8090,
            "public_ip": "127.0.0.1",
            "default_instance": "minivps",
            "instances": {}
        }
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def save_config(cfg: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    os.chmod(CONFIG_PATH, 0o644)

app = FastAPI(
    title="Mini VPS Management API",
    description="All-in-One REST API to create, control, monitor and scale fully isolated Linux Mini-VPS instances with custom CPU, RAM, and Storage limits.",
    version="2.0.0"
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

def verify_api_key(
    header_key: Optional[str] = Security(api_key_header),
    query_key: Optional[str] = Security(api_key_query)
):
    conf = load_config()
    valid_key = conf.get("api_key")
    key = header_key or query_key
    if not key or key != valid_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key. Pass via 'X-API-Key' header or '?api_key=' query param."
        )
    return key

# Models
class CommandRequest(BaseModel):
    command: str = Field(..., example="uname -a; free -m")
    timeout: Optional[int] = Field(30, example=30)

class PasswordChangeRequest(BaseModel):
    username: str = Field(..., example="vpsadmin")
    password: str = Field(..., example="NewSecurePassword123!")

class UserCreateRequest(BaseModel):
    username: str = Field(..., example="devuser")
    password: str = Field(..., example="DevSecurePass456!")
    is_sudo: Optional[bool] = Field(True, example=True)

class CreateVPSRequest(BaseModel):
    name: str = Field(..., example="client-node1")
    os_image: Optional[str] = Field("ubuntu:22.04", example="ubuntu:22.04")
    cpu: Optional[int] = Field(2, example=2)
    ram_gb: Optional[int] = Field(4, example=4)
    storage_gb: Optional[int] = Field(32, example=32)
    ssh_port: Optional[int] = Field(2223, example=2223)
    username: Optional[str] = Field("vpsadmin", example="vpsadmin")
    password: Optional[str] = Field("MiniVps#2026Pass!", example="MiniVps#2026Pass!")

@app.get("/")
def home():
    conf = load_config()
    return {
        "service": "Mini VPS Management API",
        "version": "2.0.0",
        "public_ip": conf.get("public_ip"),
        "total_instances": len(conf.get("instances", {})),
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "status": "online"
    }

@app.get("/api/vps/list", dependencies=[Depends(verify_api_key)])
def list_all_vps():
    conf = load_config()
    instances = conf.get("instances", {})
    results = []

    # Get live status from LXD
    proc = subprocess.run(["lxc", "list", "--format", "json"], capture_output=True, text=True)
    live_map = {}
    try:
        data = json.loads(proc.stdout)
        for item in data:
            live_map[item.get("name")] = item.get("status")
    except Exception:
        pass

    for name, item in instances.items():
        results.append({
            "name": name,
            "status": live_map.get(name, "UNKNOWN"),
            "cpu": item.get("cpu"),
            "ram": item.get("ram"),
            "storage_gb": item.get("storage_gb"),
            "ssh_port": item.get("ssh_port"),
            "default_user": item.get("default_user"),
            "created_at": item.get("created_at")
        })
    return {"status": "success", "instances": results}

@app.get("/api/vps/{name}/info", dependencies=[Depends(verify_api_key)])
def get_vps_info(name: str):
    conf = load_config()
    instances = conf.get("instances", {})
    if name not in instances:
        # Fallback to single instance check if default name
        if name == conf.get("container_name"):
            return {
                "name": name,
                "public_ip": conf.get("public_ip"),
                "ssh_port": conf.get("ssh_port", 2222),
                "default_user": conf.get("default_user", "vpsadmin"),
                "specs": conf.get("specs")
            }
        raise HTTPException(status_code=404, detail=f"Mini VPS '{name}' not found.")

    vps = instances[name]
    return {
        "name": name,
        "public_ip": conf.get("public_ip"),
        "ssh_port": vps.get("ssh_port"),
        "ssh_command": f"ssh -p {vps.get('ssh_port')} {vps.get('default_user')}@{conf.get('public_ip')}",
        "default_user": vps.get("default_user"),
        "specs": {
            "cpu": vps.get("cpu"),
            "ram": vps.get("ram"),
            "storage_gb": vps.get("storage_gb"),
            "os": vps.get("os")
        },
        "created_at": vps.get("created_at")
    }

@app.get("/api/vps/{name}/status", dependencies=[Depends(verify_api_key)])
def get_vps_status(name: str):
    try:
        state_proc = subprocess.run(
            ["lxc", "info", name],
            capture_output=True,
            text=True,
            check=False
        )
        if state_proc.returncode != 0:
            raise HTTPException(status_code=404, detail=f"Container '{name}' not found.")

        is_running = "Status: RUNNING" in state_proc.stdout

        if not is_running:
            return {
                "name": name,
                "status": "STOPPED",
                "is_running": False
            }

        mem_proc = subprocess.run(
            ["lxc", "exec", name, "--", "free", "-m"],
            capture_output=True,
            text=True,
            timeout=5
        )
        mem_lines = mem_proc.stdout.strip().split("\n")
        mem_data = mem_lines[1].split() if len(mem_lines) > 1 else []
        mem_total = int(mem_data[1]) if len(mem_data) > 1 else 0
        mem_used = int(mem_data[2]) if len(mem_data) > 2 else 0
        mem_free = int(mem_data[3]) if len(mem_data) > 3 else 0

        disk_proc = subprocess.run(
            ["lxc", "exec", name, "--", "df", "-h", "/"],
            capture_output=True,
            text=True,
            timeout=5
        )
        disk_lines = disk_proc.stdout.strip().split("\n")
        disk_data = disk_lines[1].split() if len(disk_lines) > 1 else []
        disk_size = disk_data[1] if len(disk_data) > 1 else "Unknown"
        disk_used = disk_data[2] if len(disk_data) > 2 else "Unknown"
        disk_avail = disk_data[3] if len(disk_data) > 3 else "Unknown"
        disk_percent = disk_data[4] if len(disk_data) > 4 else "Unknown"

        uptime_proc = subprocess.run(
            ["lxc", "exec", name, "--", "uptime", "-p"],
            capture_output=True,
            text=True,
            timeout=5
        )
        uptime = uptime_proc.stdout.strip()

        ip_proc = subprocess.run(
            ["lxc", "list", name, "--format", "json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        ip_info = []
        try:
            c_json = json.loads(ip_proc.stdout)
            if c_json and len(c_json) > 0:
                eth0 = c_json[0].get("state", {}).get("network", {}).get("eth0", {})
                addresses = eth0.get("addresses", [])
                ip_info = [a.get("address") for a in addresses]
        except Exception:
            pass

        return {
            "name": name,
            "status": "RUNNING",
            "is_running": True,
            "uptime": uptime,
            "memory": {
                "total_mb": mem_total,
                "used_mb": mem_used,
                "free_mb": mem_free,
                "usage_percent": round((mem_used / mem_total * 100), 1) if mem_total else 0
            },
            "disk": {
                "total": disk_size,
                "used": disk_used,
                "available": disk_avail,
                "usage_percent": disk_percent
            },
            "internal_ips": ip_info
        }

    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/vps/{name}/start", dependencies=[Depends(verify_api_key)])
def start_vps(name: str):
    res = subprocess.run(["lxc", "start", name], capture_output=True, text=True)
    if res.returncode != 0:
        if "already running" in res.stderr:
            return {"status": "success", "message": f"Mini VPS '{name}' is already running."}
        raise HTTPException(status_code=500, detail=res.stderr.strip())
    return {"status": "success", "message": f"Mini VPS '{name}' started successfully."}

@app.post("/api/vps/{name}/stop", dependencies=[Depends(verify_api_key)])
def stop_vps(name: str):
    res = subprocess.run(["lxc", "stop", name], capture_output=True, text=True)
    if res.returncode != 0:
        if "already stopped" in res.stderr:
            return {"status": "success", "message": f"Mini VPS '{name}' is already stopped."}
        raise HTTPException(status_code=500, detail=res.stderr.strip())
    return {"status": "success", "message": f"Mini VPS '{name}' stopped successfully."}

@app.post("/api/vps/{name}/restart", dependencies=[Depends(verify_api_key)])
def restart_vps(name: str):
    res = subprocess.run(["lxc", "restart", name], capture_output=True, text=True)
    if res.returncode != 0:
        raise HTTPException(status_code=500, detail=res.stderr.strip())
    return {"status": "success", "message": f"Mini VPS '{name}' restarted successfully."}

@app.post("/api/vps/{name}/exec", dependencies=[Depends(verify_api_key)])
def exec_in_vps(name: str, req: CommandRequest):
    try:
        proc = subprocess.run(
            ["lxc", "exec", name, "--", "bash", "-c", req.command],
            capture_output=True,
            text=True,
            timeout=req.timeout
        )
        return {
            "status": "success",
            "name": name,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail=f"Command timed out after {req.timeout} seconds.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vps/{name}/user/password", dependencies=[Depends(verify_api_key)])
def change_user_password(name: str, req: PasswordChangeRequest):
    p = subprocess.Popen(
        ["lxc", "exec", name, "--", "chpasswd"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = p.communicate(input=f"{req.username}:{req.password}\n")
    if p.returncode != 0:
        raise HTTPException(status_code=500, detail=stderr.strip() or "Failed to change password.")
    return {"status": "success", "message": f"Password for user '{req.username}' in '{name}' updated successfully."}

@app.post("/api/vps/{name}/user/create", dependencies=[Depends(verify_api_key)])
def create_new_user(name: str, req: UserCreateRequest):
    check = subprocess.run(["lxc", "exec", name, "--", "id", req.username], capture_output=True)
    if check.returncode == 0:
        raise HTTPException(status_code=400, detail=f"User '{req.username}' already exists in '{name}'.")

    cmd = ["lxc", "exec", name, "--", "useradd", "-m", "-s", "/bin/bash"]
    if req.is_sudo:
        cmd += ["-G", "sudo"]
    cmd.append(req.username)

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise HTTPException(status_code=500, detail=res.stderr.strip() or "Failed to create user.")

    p = subprocess.Popen(
        ["lxc", "exec", name, "--", "chpasswd"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    p.communicate(input=f"{req.username}:{req.password}\n")

    if req.is_sudo:
        subprocess.run(
            ["lxc", "exec", name, "--", "bash", "-c", f'echo "{req.username} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/{req.username} && chmod 440 /etc/sudoers.d/{req.username}']
        )

    return {"status": "success", "message": f"User '{req.username}' created successfully in '{name}'."}

@app.post("/api/vps/create", dependencies=[Depends(verify_api_key)])
def create_vps_instance(req: CreateVPSRequest):
    conf = load_config()
    instances = conf.setdefault("instances", {})
    if req.name in instances:
        raise HTTPException(status_code=400, detail=f"Instance '{req.name}' already exists.")

    pool_name = f"{req.name}-pool"
    
    # 1. Create Btrfs storage pool with requested storage
    subprocess.run(
        ["lxc", "storage", "create", pool_name, "btrfs", f"size={req.storage_gb}GiB"],
        capture_output=True,
        text=True
    )

    # 2. Launch LXD container with resource limits
    launch_res = subprocess.run(
        [
            "lxc", "launch", req.os_image, req.name,
            "--storage", pool_name,
            "-c", f"limits.cpu={req.cpu}",
            "-c", f"limits.memory={req.ram_gb}GiB"
        ],
        capture_output=True,
        text=True
    )
    if launch_res.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Launch failed: {launch_res.stderr.strip()}")

    # 3. Add SSH port proxy
    subprocess.run(
        [
            "lxc", "config", "device", "add", req.name, f"ssh-{req.name}", "proxy",
            f"listen=tcp:0.0.0.0:{req.ssh_port}", "connect=tcp:127.0.0.1:22"
        ],
        capture_output=True,
        text=True
    )

    # 4. Set boot autostart
    subprocess.run(["lxc", "config", "set", req.name, "boot.autostart", "true"])

    # 5. Enable password authentication
    subprocess.run(["lxc", "exec", req.name, "--", "sed", "-i", "s/^#*PasswordAuthentication.*/PasswordAuthentication yes/", "/etc/ssh/sshd_config"])
    subprocess.run(["lxc", "exec", req.name, "--", "bash", "-c", "sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config.d/* 2>/dev/null || true"])
    subprocess.run(["lxc", "exec", req.name, "--", "sed", "-i", "s/^#*PermitRootLogin.*/PermitRootLogin yes/", "/etc/ssh/sshd_config"])

    # 6. Create admin user
    subprocess.run(["lxc", "exec", req.name, "--", "useradd", "-m", "-s", "/bin/bash", "-G", "sudo", req.username])
    p = subprocess.Popen(["lxc", "exec", req.name, "--", "chpasswd"], stdin=subprocess.PIPE, text=True)
    p.communicate(input=f"{req.username}:{req.password}\nroot:{req.password}\n")

    subprocess.run(["lxc", "exec", req.name, "--", "bash", "-c", f'echo "{req.username} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/{req.username} && chmod 440 /etc/sudoers.d/{req.username}'])
    subprocess.run(["lxc", "exec", req.name, "--", "systemctl", "restart", "ssh"])

    # 7. Save to config
    instances[req.name] = {
        "name": req.name,
        "os": req.os_image,
        "cpu": req.cpu,
        "ram": f"{req.ram_gb}GiB",
        "storage_gb": req.storage_gb,
        "storage_pool": pool_name,
        "ssh_port": req.ssh_port,
        "default_user": req.username,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    save_config(conf)

    return {
        "status": "success",
        "message": f"Mini VPS '{req.name}' created and started successfully.",
        "details": instances[req.name],
        "ssh_command": f"ssh -p {req.ssh_port} {req.username}@{conf.get('public_ip')}"
    }

@app.delete("/api/vps/{name}", dependencies=[Depends(verify_api_key)])
def delete_vps_instance(name: str):
    conf = load_config()
    instances = conf.get("instances", {})
    if name not in instances:
        raise HTTPException(status_code=404, detail=f"Mini VPS '{name}' not found.")

    vps = instances[name]
    pool = vps.get("storage_pool")

    # Stop and delete container
    subprocess.run(["lxc", "stop", name, "--force"], capture_output=True)
    subprocess.run(["lxc", "delete", name], capture_output=True)

    # Delete storage pool if dedicated
    if pool and pool != "default":
        subprocess.run(["lxc", "storage", "delete", pool], capture_output=True)

    del instances[name]
    save_config(conf)

    return {"status": "success", "message": f"Mini VPS '{name}' and its storage pool deleted successfully."}
