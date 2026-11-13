import os
import json
import secrets
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from pydantic import BaseModel, Field

from vps_utils import (
    get_container_bandwidth,
    get_container_expiry,
    enforce_limits_and_expiry,
    format_bytes
)

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
    description="All-in-One REST API to create, control, monitor, set bandwidth quotas and manage lifespans for isolated Linux Mini-VPS instances.",
    version="2.1.0"
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

# Request Models
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

class RenewRequest(BaseModel):
    days: int = Field(30, example=30, description="Number of additional days to extend")

class LimitRequest(BaseModel):
    bandwidth_limit_gb: Optional[float] = Field(None, example=100.0, description="Total data transfer quota in GB (0 for unlimited)")
    speed_limit: Optional[str] = Field(None, example="50Mbit", description="Speed limit rate (e.g. 50Mbit, 100Mbit, or 'none')")

class CreateVPSRequest(BaseModel):
    name: str = Field(..., example="client-node1")
    os_image: Optional[str] = Field("ubuntu:22.04", example="ubuntu:22.04")
    cpu: Optional[int] = Field(2, example=2)
    ram_gb: Optional[int] = Field(4, example=4)
    storage_gb: Optional[int] = Field(32, example=32)
    ssh_port: Optional[int] = Field(2223, example=2223)
    username: Optional[str] = Field("vpsadmin", example="vpsadmin")
    password: Optional[str] = Field("MiniVps#2026Pass!", example="MiniVps#2026Pass!")
    duration_days: Optional[int] = Field(30, example=30, description="Active lifespan in days (0 for unlimited)")
    bandwidth_limit_gb: Optional[float] = Field(100.0, example=100.0, description="Bandwidth quota in GB (0 for unlimited)")
    speed_limit: Optional[str] = Field(None, example="100Mbit", description="Network rate limit (e.g. 50Mbit, 100Mbit)")

@app.get("/")
def home():
    conf = load_config()
    return {
        "service": "Mini VPS Management API",
        "version": "2.1.0",
        "public_ip": conf.get("public_ip"),
        "total_instances": len(conf.get("instances", {})),
        "docs_url": "/docs",
        "status": "online"
    }

@app.get("/api/vps/list", dependencies=[Depends(verify_api_key)])
def list_all_vps():
    conf = load_config()
    instances = conf.get("instances", {})
    results = []

    proc = subprocess.run(["lxc", "list", "--format", "json"], capture_output=True, text=True)
    live_map = {}
    try:
        data = json.loads(proc.stdout)
        for item in data:
            live_map[item.get("name")] = item.get("status")
    except Exception:
        pass

    for name, item in instances.items():
        limit_gb = float(item.get("bandwidth_limit_gb", 0))
        bw = get_container_bandwidth(name, limit_gb)
        exp = get_container_expiry(item)

        results.append({
            "name": name,
            "status": live_map.get(name, "UNKNOWN"),
            "cpu": item.get("cpu"),
            "ram": item.get("ram"),
            "storage_gb": item.get("storage_gb"),
            "ssh_port": item.get("ssh_port"),
            "default_user": item.get("default_user"),
            "bandwidth": {
                "used": bw.get("total_human"),
                "limit": bw.get("limit_human"),
                "usage_percent": bw.get("usage_percent"),
                "is_exceeded": bw.get("is_exceeded")
            },
            "expiry": {
                "duration_days": exp.get("duration_days"),
                "expires_at": exp.get("expires_at"),
                "days_remaining": exp.get("days_remaining"),
                "is_expired": exp.get("is_expired"),
                "status_label": exp.get("status_label")
            },
            "created_at": item.get("created_at")
        })
    return {"status": "success", "instances": results}

@app.get("/api/vps/{name}/info", dependencies=[Depends(verify_api_key)])
def get_vps_info(name: str):
    conf = load_config()
    instances = conf.get("instances", {})
    if name not in instances:
        raise HTTPException(status_code=404, detail=f"Mini VPS '{name}' not found.")

    vps = instances[name]
    limit_gb = float(vps.get("bandwidth_limit_gb", 0))
    bw = get_container_bandwidth(name, limit_gb)
    exp = get_container_expiry(vps)

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
        "bandwidth": bw,
        "expiry": exp,
        "created_at": vps.get("created_at")
    }

@app.get("/api/vps/{name}/status", dependencies=[Depends(verify_api_key)])
def get_vps_status(name: str):
    try:
        conf = load_config()
        vps = conf.get("instances", {}).get(name, {})
        limit_gb = float(vps.get("bandwidth_limit_gb", 0))

        state_proc = subprocess.run(["lxc", "info", name], capture_output=True, text=True, check=False)
        if state_proc.returncode != 0:
            raise HTTPException(status_code=404, detail=f"Container '{name}' not found.")

        is_running = "Status: RUNNING" in state_proc.stdout
        bw = get_container_bandwidth(name, limit_gb)
        exp = get_container_expiry(vps) if vps else {}

        if not is_running:
            return {
                "name": name,
                "status": "STOPPED",
                "is_running": False,
                "bandwidth": bw,
                "expiry": exp
            }

        mem_proc = subprocess.run(["lxc", "exec", name, "--", "free", "-m"], capture_output=True, text=True, timeout=5)
        mem_lines = mem_proc.stdout.strip().split("\n")
        mem_data = mem_lines[1].split() if len(mem_lines) > 1 else []
        mem_total = int(mem_data[1]) if len(mem_data) > 1 else 0
        mem_used = int(mem_data[2]) if len(mem_data) > 2 else 0
        mem_free = int(mem_data[3]) if len(mem_data) > 3 else 0

        disk_proc = subprocess.run(["lxc", "exec", name, "--", "df", "-h", "/"], capture_output=True, text=True, timeout=5)
        disk_lines = disk_proc.stdout.strip().split("\n")
        disk_data = disk_lines[1].split() if len(disk_lines) > 1 else []
        disk_size = disk_data[1] if len(disk_data) > 1 else "Unknown"
        disk_used = disk_data[2] if len(disk_data) > 2 else "Unknown"
        disk_avail = disk_data[3] if len(disk_data) > 3 else "Unknown"
        disk_percent = disk_data[4] if len(disk_data) > 4 else "Unknown"

        uptime_proc = subprocess.run(["lxc", "exec", name, "--", "uptime", "-p"], capture_output=True, text=True, timeout=5)
        uptime = uptime_proc.stdout.strip()

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
            "bandwidth": bw,
            "expiry": exp
        }

    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/vps/{name}/renew", dependencies=[Depends(verify_api_key)])
def renew_vps(name: str, req: RenewRequest):
    conf = load_config()
    instances = conf.get("instances", {})
    if name not in instances:
        raise HTTPException(status_code=404, detail=f"Mini VPS '{name}' not found.")

    vps = instances[name]
    exp_str = vps.get("expires_at")
    now = datetime.utcnow()

    if exp_str:
        try:
            curr_exp = datetime.fromisoformat(exp_str.replace("Z", "+00:00")).replace(tzinfo=None)
            base_date = max(now, curr_exp)
        except Exception:
            base_date = now
    else:
        base_date = now

    new_exp = base_date + timedelta(days=req.days)
    vps["expires_at"] = new_exp.isoformat() + "Z"
    vps["duration_days"] = int(vps.get("duration_days", 0)) + req.days
    if vps.get("suspended_reason") == "EXPIRED":
        vps.pop("suspended_reason", None)
        subprocess.run(["lxc", "start", name], capture_output=True)

    save_config(conf)
    return {
        "status": "success",
        "message": f"Mini-VPS '{name}' renewed by {req.days} days. New expiration: {vps['expires_at']}",
        "new_expiration": vps["expires_at"]
    }

@app.post("/api/vps/{name}/limit", dependencies=[Depends(verify_api_key)])
def update_limits(name: str, req: LimitRequest):
    conf = load_config()
    instances = conf.get("instances", {})
    if name not in instances:
        raise HTTPException(status_code=404, detail=f"Mini VPS '{name}' not found.")

    vps = instances[name]
    if req.bandwidth_limit_gb is not None:
        vps["bandwidth_limit_gb"] = req.bandwidth_limit_gb
        if vps.get("suspended_reason") == "BANDWIDTH_EXCEEDED":
            bw = get_container_bandwidth(name, req.bandwidth_limit_gb)
            if not bw.get("is_exceeded"):
                vps.pop("suspended_reason", None)
                subprocess.run(["lxc", "start", name], capture_output=True)

    if req.speed_limit is not None:
        if req.speed_limit.lower() in ["none", "0", "unlimited"]:
            subprocess.run(["lxc", "config", "device", "remove", name, "eth0"], capture_output=True)
            vps.pop("speed_limit", None)
        else:
            subprocess.run(["lxc", "config", "device", "override", name, "eth0", f"limits.max={req.speed_limit}"], capture_output=True)
            vps["speed_limit"] = req.speed_limit

    save_config(conf)
    return {"status": "success", "message": f"Limits for '{name}' updated successfully.", "details": vps}

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

@app.post("/api/vps/create", dependencies=[Depends(verify_api_key)])
def create_vps_instance(req: CreateVPSRequest):
    conf = load_config()
    instances = conf.setdefault("instances", {})
    if req.name in instances:
        raise HTTPException(status_code=400, detail=f"Instance '{req.name}' already exists.")

    pool_name = f"{req.name}-pool"
    subprocess.run(["lxc", "storage", "create", pool_name, "btrfs", f"size={req.storage_gb}GiB"], capture_output=True)

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

    # Add SSH port proxy
    subprocess.run(
        [
            "lxc", "config", "device", "add", req.name, f"ssh-{req.name}", "proxy",
            f"listen=tcp:0.0.0.0:{req.ssh_port}", "connect=tcp:127.0.0.1:22"
        ],
        capture_output=True
    )

    if req.speed_limit:
        subprocess.run(["lxc", "config", "device", "override", req.name, "eth0", f"limits.max={req.speed_limit}"], capture_output=True)

    subprocess.run(["lxc", "config", "set", req.name, "boot.autostart", "true"])

    # Configure SSH and User
    subprocess.run(["lxc", "exec", req.name, "--", "sed", "-i", "s/^#*PasswordAuthentication.*/PasswordAuthentication yes/", "/etc/ssh/sshd_config"])
    subprocess.run(["lxc", "exec", req.name, "--", "bash", "-c", "sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config.d/* 2>/dev/null || true"])
    subprocess.run(["lxc", "exec", req.name, "--", "sed", "-i", "s/^#*PermitRootLogin.*/PermitRootLogin yes/", "/etc/ssh/sshd_config"])

    subprocess.run(["lxc", "exec", req.name, "--", "useradd", "-m", "-s", "/bin/bash", "-G", "sudo", req.username])
    p = subprocess.Popen(["lxc", "exec", req.name, "--", "chpasswd"], stdin=subprocess.PIPE, text=True)
    p.communicate(input=f"{req.username}:{req.password}\nroot:{req.password}\n")

    subprocess.run(["lxc", "exec", req.name, "--", "bash", "-c", f'echo "{req.username} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/{req.username} && chmod 440 /etc/sudoers.d/{req.username}'])
    subprocess.run(["lxc", "exec", req.name, "--", "systemctl", "restart", "ssh"])

    now = datetime.utcnow()
    exp_at = (now + timedelta(days=req.duration_days)).isoformat() + "Z" if req.duration_days and req.duration_days > 0 else None

    instances[req.name] = {
        "name": req.name,
        "os": req.os_image,
        "cpu": req.cpu,
        "ram": f"{req.ram_gb}GiB",
        "storage_gb": req.storage_gb,
        "storage_pool": pool_name,
        "ssh_port": req.ssh_port,
        "default_user": req.username,
        "duration_days": req.duration_days or 0,
        "bandwidth_limit_gb": req.bandwidth_limit_gb or 0.0,
        "speed_limit": req.speed_limit or "None",
        "created_at": now.isoformat() + "Z",
        "expires_at": exp_at
    }
    save_config(conf)

    return {
        "status": "success",
        "message": f"Mini VPS '{req.name}' created successfully.",
        "details": instances[req.name],
        "ssh_command": f"ssh -p {req.ssh_port} {req.username}@{conf.get('public_ip')}"
    }

@app.post("/api/vps/auto-clean", dependencies=[Depends(verify_api_key)])
def trigger_auto_clean(delete_expired: bool = False):
    result = enforce_limits_and_expiry(delete_expired=delete_expired)
    return {"status": "success", "summary": result}

@app.delete("/api/vps/{name}", dependencies=[Depends(verify_api_key)])
def delete_vps_instance(name: str):
    conf = load_config()
    instances = conf.get("instances", {})
    if name not in instances:
        raise HTTPException(status_code=404, detail=f"Mini VPS '{name}' not found.")

    vps = instances[name]
    pool = vps.get("storage_pool")

    subprocess.run(["lxc", "stop", name, "--force"], capture_output=True)
    subprocess.run(["lxc", "delete", name], capture_output=True)

    if pool and pool != "default":
        subprocess.run(["lxc", "storage", "delete", pool], capture_output=True)

    del instances[name]
    save_config(conf)

    return {"status": "success", "message": f"Mini VPS '{name}' and its storage pool deleted successfully."}
