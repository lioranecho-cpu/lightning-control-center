
import subprocess
import json
import os
import time
from datetime import datetime, timezone
import time as time_module
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Lightning Control Center API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK = os.environ.get("LCC_MOCK", "false").lower() == "true"

MOCK_DATA = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))

def run_lncli(*args):
    try:
        result = subprocess.run(["lncli"] + list(args), capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"lncli error: {result.stderr.strip()}")
        return json.loads(result.stdout)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="lncli not found")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="lncli timed out")

def run_bitcoin_cli(*args):
    try:
        result = subprocess.run(["/snap/bitcoin-core/current/bin/bitcoin-cli", "-rpcuser=luca", "-rpcpassword=bitcoinnode2026"] + list(args), capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"bitcoin-cli error: {result.stderr.strip()}")
        return json.loads(result.stdout)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="bitcoin-cli not found")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="bitcoin-cli timed out")

@app.get("/")
def root():
    return {"name": "Lightning Control Center API", "version": "0.1.0", "mock": MOCK}

@app.get("/api/node")
def get_node_info():
    if MOCK:
        return MOCK_DATA["node"]
    info = run_lncli("getinfo")
    return {
        "alias": info.get("alias"),
        "pubkey": info.get("identity_pubkey"),
        "version": info.get("version"),
        "status": "online",
        "synced_to_chain": info.get("synced_to_chain"),
        "synced_to_graph": info.get("synced_to_graph"),
        "block_height": info.get("block_height"),
        "num_peers": info.get("num_peers"),
        "uptime_seconds": 0,
    }

def get_btc_price():
    try:
        import urllib.request
        url = "https://mempool.space/api/v1/prices"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
            return data.get("USD", 0)
    except:
        return 0

@app.get("/api/wallet")
def get_wallet():
    if MOCK:
        return MOCK_DATA["wallet"]
    on_chain = run_lncli("walletbalance")
    channel = run_lncli("channelbalance")
    return {
        "total_balance": int(on_chain.get("total_balance", 0)),
        "confirmed_balance": int(on_chain.get("confirmed_balance", 0)),
        "unconfirmed_balance": int(on_chain.get("unconfirmed_balance", 0)),
        "channel_balance": int(channel.get("balance", 0)),
        "btc_price_usd": get_btc_price(),
    }

@app.get("/api/channels")
def get_channels():
    if MOCK:
        return MOCK_DATA["channels"]
    active = run_lncli("listchannels")
    pending = run_lncli("pendingchannels")
    channel_list = []
    for ch in active.get("channels", []):
        channel_list.append({
            "peer_alias": ch.get("peer_alias", ch.get("remote_pubkey", "")[:12] + "..."),
            "capacity": int(ch.get("capacity", 0)),
            "local_balance": int(ch.get("local_balance", 0)),
            "remote_balance": int(ch.get("remote_balance", 0)),
            "fee_ppm": 0,
            "base_fee": 0,
            "status": "active" if ch.get("active") else "inactive",
        })
    return {
        "num_active": len([c for c in channel_list if c["status"] == "active"]),
        "num_inactive": len([c for c in channel_list if c["status"] == "inactive"]),
        "num_pending": len(pending.get("pending_open_channels", [])),
        "total_capacity": sum(c["capacity"] for c in channel_list),
        "list": channel_list,
    }

@app.get("/api/routing")
def get_routing():
    if MOCK:
        return MOCK_DATA["routing"]
    # Fetch all time history
    history_all = run_lncli("fwdinghistory", "--max_events=10000")
    events_all = history_all.get("forwarding_events", [])
    now_ts = int(time.time())
    events = [e for e in events_all if int(e.get("timestamp",0)) >= now_ts - (30*86400)]
    events_60 = [e for e in events_all if int(e.get("timestamp",0)) >= now_ts - (60*86400)]
    total_fees = sum(int(e.get("fee", 0)) for e in events)
    total_fees_60 = sum(int(e.get("fee", 0)) for e in events_60)
    total_fees_all = sum(int(e.get("fee", 0)) for e in events_all)
    total_vol = sum(int(e.get("amt_out", 0)) for e in events)
    daily_fees = [0] * 30
    daily_volume = [0] * 30
    now = time.time()
    for e in events:
        ts = int(e.get("timestamp", 0))
        day = int((now - ts) / 86400)
        if 0 <= day < 30:
            idx = 29 - day
            daily_fees[idx] += int(e.get("fee", 0))
            daily_volume[idx] += int(e.get("amt_out", 0))
    return {
        "fees_30d_sats": total_fees,
        "fees_60d_sats": total_fees_60,
        "fees_alltime_sats": total_fees_all,
        "volume_30d_btc": round(total_vol / 100_000_000, 8),
        "forwarding_events": events[-10:],
        "daily_fees": daily_fees,
        "daily_volume": [round(v / 100_000_000, 8) for v in daily_volume],
    }

@app.get("/api/mempool")
def get_mempool():
    if MOCK:
        return MOCK_DATA["mempool"]
    info = run_bitcoin_cli("getmempoolinfo")
    fee_info = run_bitcoin_cli("estimatesmartfee", "6")
    size_mb = round(info.get("bytes", 0) / 1_000_000, 1)
    fee_sat_vbyte = round(fee_info.get("feerate", 0.00001) * 100_000_000 / 1000, 1)
    congestion = "Low" if size_mb < 5 else "Medium" if size_mb < 50 else "High"
    return {"size_mb": size_mb, "fee_sat_vbyte": fee_sat_vbyte, "congestion": congestion}

@app.get("/api/mining")
def get_mining():
    return MOCK_DATA["mining"]

@app.get("/api/dashboard")
def get_dashboard():
    return {
        "node": get_node_info(),
        "wallet": get_wallet(),
        "channels": get_channels(),
        "routing": get_routing(),
        "mempool": get_mempool(),
        "mining": get_mining(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/peers")
def get_peers():
    if MOCK:
        return {"peers": []}
    result = run_lncli("listpeers")
    channels = run_lncli("listchannels")
    channel_pubkeys = {ch.get("remote_pubkey") for ch in channels.get("channels", [])}
    peers = []
    for p in result.get("peers", []):
        pubkey = p.get("pub_key")
        peers.append({
            "pub_key": pubkey,
            "alias": p.get("peer_alias", "Unknown"),
            "address": p.get("address", ""),
            "bytes_sent": int(p.get("bytes_sent", 0)),
            "bytes_recv": int(p.get("bytes_recv", 0)),
            "ping_time": int(p.get("ping_time", 0)),
            "sync_type": p.get("sync_type", ""),
            "has_channel": pubkey in channel_pubkeys,
        })
    return {"peers": peers}


@app.get("/api/newaddress")
def get_new_address(request: Request):
    if not MOCK and request.headers.get("x-api-key") != "lcc-local-only":
        raise HTTPException(status_code=403, detail="Not authorized")
    if MOCK:
        return {"address": "bc1qmockaddress000000000000000000000000000"}
    result = run_lncli("newaddress", "p2wkh")
    return {"address": result.get("address")}
@app.get("/api/transactions")
def get_transactions(limit: int = 10):
    if MOCK:
        return {"transactions": []}
    
    transactions = []
    
    # Get sent payments
    try:
        payments = run_lncli("listpayments", f"--max_payments={limit if limit > 0 else 1000}")
        for p in payments.get("payments", []):
            if p.get("status") == "SUCCEEDED":
                transactions.append({
                    "type": "sent",
                    "amount": int(p.get("value_sat", 0)),
                    "fee": int(p.get("fee_sat", 0)),
                    "desc": "Lightning payment sent",
                    "status": "confirmed",
                    "time": int(p.get("creation_date", 0))
                })
    except:
        pass

    # Get received invoices
    try:
        invoices = run_lncli("listinvoices", f"--num_max_invoices={limit if limit > 0 else 1000}")
        for inv in invoices.get("invoices", []):
            if inv.get("state") == "SETTLED":
                transactions.append({
                    "type": "received",
                    "amount": int(inv.get("amt_paid_sat", 0)),
                    "fee": 0,
                    "desc": inv.get("memo", "Lightning payment received"),
                    "status": "confirmed",
                    "time": int(inv.get("settle_date", 0))
                })
    except:
        pass

    # Get routing fees
    try:
        fwd = run_lncli("fwdinghistory", "--max_events=20")
        for e in fwd.get("forwarding_events", []):
            transactions.append({
                "type": "forwarded",
                "amount": int(e.get("amt_out", 0)),
                "fee": int(e.get("fee", 0)),
                "desc": f"Routed {e.get('peer_alias_in','?')} → {e.get('peer_alias_out','?')}",
                "status": "confirmed",
                "time": int(e.get("timestamp", 0))
            })
    except:
        pass

    # Sort by time descending
    transactions.sort(key=lambda x: x["time"], reverse=True)
    # Convert unix timestamps to human readable
    now = time_module.time()
    for tx in transactions:
        t = tx["time"]
        diff = now - t
        if diff < 3600: tx["time"] = f"{int(diff/60)} min ago"
        elif diff < 86400: tx["time"] = f"{int(diff/3600)} hours ago"
        elif diff < 604800: tx["time"] = f"{int(diff/86400)} days ago"
        else: tx["time"] = datetime.fromtimestamp(t).strftime("%b %d %Y")
    
    return {"transactions": transactions[:20]}

@app.get("/api/system")
def get_system():
    import subprocess, platform, socket
    
    try:
        import psutil
        cpu_pct = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        ram_pct = ram.percent
        ram_used_gb = round(ram.used / 1024**3, 1)
        ram_total_gb = round(ram.total / 1024**3, 1)
        
        # Disk usage
        try:
            bitcoin_disk = psutil.disk_usage('/mnt/bitcoin')
        except:
            bitcoin_disk = psutil.disk_usage('/')
        bitcoin_disk_pct = bitcoin_disk.percent
        bitcoin_disk_used = f"{bitcoin_disk.used / 1024**3:.1f} GB"
        bitcoin_disk_total = f"{bitcoin_disk.total / 1024**3:.0f} GB"
        
        root_disk = psutil.disk_usage('/')
        root_disk_pct = root_disk.percent
        
        cpu_cores = psutil.cpu_count()
        
        # Uptime
        import time
        boot_time = psutil.boot_time()
        uptime_secs = int(time.time() - boot_time)
        days = uptime_secs // 86400
        hours = (uptime_secs % 86400) // 3600
        mins = (uptime_secs % 3600) // 60
        uptime_str = f"{days}d {hours}h {mins}m"
        
    except ImportError:
        cpu_pct = 0
        ram_pct = 0
        ram_used_gb = 0
        ram_total_gb = 0
        bitcoin_disk_pct = 0
        bitcoin_disk_used = "N/A"
        bitcoin_disk_total = "N/A"
        root_disk_pct = 0
        cpu_cores = 0
        uptime_str = "N/A"
    
    # System info
    hostname = socket.gethostname()
    os_info = f"{platform.system()} {platform.release()}"
    kernel = platform.release()
    arch = platform.machine()
    
    # Services
    services = [
        {"name": "Bitcoin Core", "desc": "Full Bitcoin node — validates blocks and transactions", "unit": "bitcoin-core"},
        {"name": "LND / litd", "desc": "Lightning Network Daemon — manages payment channels", "unit": "litd"},
        {"name": "RTL", "desc": "Ride The Lightning — web UI for LND", "unit": "rtl"},
        {"name": "LNbits", "desc": "Lightning wallet and extensions platform", "unit": "lnbits"},
        {"name": "Cloudflare Tunnel", "desc": "Secure remote access tunnel", "unit": "cloudflared"},
        {"name": "LCC", "desc": "Lightning Control Center — this app", "unit": "lcc"},
        {"name": "Tor", "desc": "Anonymous routing for Lightning connections", "unit": "tor"},
        {"name": "Caddy", "desc": "Reverse proxy and HTTPS server", "unit": "caddy"},
    ]
    
    for svc in services:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", svc["unit"]],
                capture_output=True, text=True, timeout=3
            )
            svc["active"] = result.stdout.strip() == "active"
            svc["status"] = result.stdout.strip()
        except:
            svc["active"] = False
            svc["status"] = "unknown"
        del svc["unit"]
    
    return {
        "cpu_percent": cpu_pct,
        "cpu_cores": cpu_cores,
        "ram_percent": ram_pct,
        "ram_used_gb": ram_used_gb,
        "ram_total_gb": ram_total_gb,
        "bitcoin_disk_percent": bitcoin_disk_pct,
        "bitcoin_disk_used": bitcoin_disk_used,
        "bitcoin_disk_total": bitcoin_disk_total,
        "root_disk_percent": root_disk_pct,
        "uptime": uptime_str,
        "hostname": hostname,
        "os": os_info,
        "kernel": kernel,
        "arch": arch,
        "services": services,
    }

app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/dashboard")
def dashboard():
    return FileResponse("index.html")

@app.get("/api/tier")
def get_tier():
    data = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))
    return {"tier": data.get("tier", "community")}

@app.post("/api/tier/{key}")
def set_tier(key: str):
    KEYS = {
        "LCC-PERSONAL-2025": "personal",
        "LCC-PRO-2025": "pro"
    }
    if key not in KEYS:
        raise HTTPException(status_code=403, detail="Invalid license key")
    data = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))
    data["tier"] = KEYS[key]
    with open(os.path.join(os.path.dirname(__file__), "data.json"), "w") as f:
        json.dump(data, f, indent=2)
    return {"tier": data["tier"], "status": "activated"}
