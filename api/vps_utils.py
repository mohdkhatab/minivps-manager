import os
import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple

CONFIG_PATH = "/etc/minivps/config.json"
BANDWIDTH_PATH = "/etc/minivps/bandwidth.json"

def format_bytes(size: float) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if abs(size) < 1024.0:
            return f"{size:3.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def load_bandwidth_db() -> Dict[str, Any]:
    if os.path.exists(BANDWIDTH_PATH):
        try:
            with open(BANDWIDTH_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_bandwidth_db(db: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(BANDWIDTH_PATH), exist_ok=True)
    with open(BANDWIDTH_PATH, "w") as f:
        json.dump(db, f, indent=2)
    try:
        os.chmod(BANDWIDTH_PATH, 0o666)
    except Exception:
        pass

def get_container_bandwidth(name: str, limit_gb: float = 0.0) -> Dict[str, Any]:
    db = load_bandwidth_db()
    c_data = db.get(name, {
        "accumulated_rx": 0,
        "accumulated_tx": 0,
        "last_raw_rx": 0,
        "last_raw_tx": 0,
        "total_rx": 0,
        "total_tx": 0,
        "last_updated": datetime.utcnow().isoformat() + "Z"
    })

    cur_rx, cur_tx = 0, 0
    try:
        proc = subprocess.run(["lxc", "query", f"/1.0/instances/{name}/state"], capture_output=True, text=True, check=True)
        qdata = json.loads(proc.stdout)
        counters = qdata.get("network", {}).get("eth0", {}).get("counters", {})
        cur_rx = counters.get("bytes_received", 0)
        cur_tx = counters.get("bytes_sent", 0)
    except Exception:
        pass

    # Detect reboot (counter reset)
    if cur_rx < c_data.get("last_raw_rx", 0):
        c_data["accumulated_rx"] = c_data.get("accumulated_rx", 0) + c_data.get("last_raw_rx", 0)
    if cur_tx < c_data.get("last_raw_tx", 0):
        c_data["accumulated_tx"] = c_data.get("accumulated_tx", 0) + c_data.get("last_raw_tx", 0)

    c_data["last_raw_rx"] = cur_rx
    c_data["last_raw_tx"] = cur_tx
    c_data["total_rx"] = c_data["accumulated_rx"] + cur_rx
    c_data["total_tx"] = c_data["accumulated_tx"] + cur_tx
    c_data["last_updated"] = datetime.utcnow().isoformat() + "Z"

    db[name] = c_data
    save_bandwidth_db(db)

    total_bytes = c_data["total_rx"] + c_data["total_tx"]
    limit_bytes = int(limit_gb * (1024 ** 3)) if limit_gb > 0 else 0
    usage_pct = round((total_bytes / limit_bytes * 100), 2) if limit_bytes > 0 else 0.0
    is_exceeded = (total_bytes >= limit_bytes) if limit_bytes > 0 else False

    return {
        "rx_bytes": c_data["total_rx"],
        "tx_bytes": c_data["total_tx"],
        "total_bytes": total_bytes,
        "rx_human": format_bytes(c_data["total_rx"]),
        "tx_human": format_bytes(c_data["total_tx"]),
        "total_human": format_bytes(total_bytes),
        "limit_gb": limit_gb,
        "limit_human": f"{limit_gb} GB" if limit_gb > 0 else "Unlimited",
        "usage_percent": usage_pct,
        "is_exceeded": is_exceeded,
        "remaining_human": format_bytes(max(0, limit_bytes - total_bytes)) if limit_bytes > 0 else "Unlimited"
    }

def get_container_expiry(vps_entry: Dict[str, Any]) -> Dict[str, Any]:
    duration_days = int(vps_entry.get("duration_days", 0))
    created_at_str = vps_entry.get("created_at")
    expires_at_str = vps_entry.get("expires_at")

    if duration_days <= 0 or not expires_at_str:
        return {
            "duration_days": 0,
            "created_at": created_at_str or "Unknown",
            "expires_at": "Never",
            "days_remaining": 9999,
            "is_expired": False,
            "status_label": "UNLIMITED"
        }

    try:
        exp_dt = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        now = datetime.now(exp_dt.tzinfo)
        diff = exp_dt - now
        days_rem = diff.days if diff.total_seconds() > 0 else (diff.days - 1 if diff.days < 0 else 0)
        is_expired = diff.total_seconds() <= 0
        return {
            "duration_days": duration_days,
            "created_at": created_at_str,
            "expires_at": expires_at_str,
            "days_remaining": max(0, days_rem) if not is_expired else 0,
            "is_expired": is_expired,
            "status_label": "EXPIRED" if is_expired else f"{max(0, days_rem)} days left"
        }
    except Exception:
        return {
            "duration_days": duration_days,
            "created_at": created_at_str or "Unknown",
            "expires_at": expires_at_str or "Unknown",
            "days_remaining": 0,
            "is_expired": False,
            "status_label": "ACTIVE"
        }

def enforce_limits_and_expiry(delete_expired: bool = False) -> Dict[str, Any]:
    if not os.path.exists(CONFIG_PATH):
        return {"actions": [], "scanned": 0}

    with open(CONFIG_PATH, "r") as f:
        conf = json.load(f)

    instances = conf.get("instances", {})
    actions = []

    for name, vps in list(instances.items()):
        # 1. Check Expiry
        exp_info = get_container_expiry(vps)
        if exp_info.get("is_expired"):
            if delete_expired:
                subprocess.run(["lxc", "stop", name, "--force"], capture_output=True)
                subprocess.run(["lxc", "delete", name], capture_output=True)
                pool = vps.get("storage_pool")
                if pool and pool != "default":
                    subprocess.run(["lxc", "storage", "delete", pool], capture_output=True)
                del instances[name]
                actions.append(f"DELETED '{name}' due to expiration ({exp_info.get('expires_at')}).")
            else:
                subprocess.run(["lxc", "stop", name], capture_output=True)
                vps["suspended_reason"] = "EXPIRED"
                actions.append(f"SUSPENDED '{name}' due to expiration ({exp_info.get('expires_at')}).")
            continue

        # 2. Check Bandwidth Limit
        limit_gb = float(vps.get("bandwidth_limit_gb", 0))
        if limit_gb > 0:
            bw_info = get_container_bandwidth(name, limit_gb)
            if bw_info.get("is_exceeded"):
                subprocess.run(["lxc", "stop", name], capture_output=True)
                vps["suspended_reason"] = "BANDWIDTH_EXCEEDED"
                actions.append(f"SUSPENDED '{name}' due to bandwidth quota exceeded ({bw_info.get('total_human')} / {bw_info.get('limit_human')}).")

    with open(CONFIG_PATH, "w") as f:
        json.dump(conf, f, indent=2)

    return {"actions": actions, "scanned": len(instances)}
