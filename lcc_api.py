
import subprocess
import threading
import json
import os
from dotenv import load_dotenv
load_dotenv()
import time
from datetime import datetime, timezone
import time as time_module
from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Lightning Control Center API", version="0.1.0")
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://lcc.satslist.shop", "http://localhost:8765", "http://192.168.4.76:8765"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK = os.environ.get("LCC_MOCK", "false").lower() == "true"

MOCK_DATA = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))

def run_lncli(*args):
    try:
        timeout = 60 if "sendpayment" in args else 10
        result = subprocess.run(["lncli"] + list(args), capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"lncli error: {result.stderr.strip()}")
        return json.loads(result.stdout)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="lncli not found")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="lncli timed out")

def run_bitcoin_cli(*args):
    try:
        rpc_user = os.getenv("RPC_USER", "")
        rpc_pass = os.getenv("RPC_PASS", "")
        result = subprocess.run(["/snap/bitcoin-core/current/bin/bitcoin-cli", f"-rpcuser={rpc_user}", f"-rpcpassword={rpc_pass}"] + list(args), capture_output=True, text=True, timeout=10)
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
        "auto_rebalance_hours": json.load(open(os.path.join(os.path.dirname(__file__), "data.json"))).get("auto_rebalance_hours", 24),
        "rebalance_amount": json.load(open(os.path.join(os.path.dirname(__file__), "data.json"))).get("rebalance_amount", 50000),
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
    # Build fee lookup from feereport using channel_point
    fee_lookup = {}
    try:
        feereport = run_lncli("feereport")
        for f in feereport.get("channel_fees", []):
            cp = f.get("channel_point", "")
            fee_lookup[cp] = {
                "fee_ppm": int(f.get("fee_per_mil", 0)),
                "base_fee": int(f.get("base_fee_msat", 0))
            }
    except:
        pass
    for ch in active.get("channels", []):
        channel_list.append({
            "peer_alias": ch.get("peer_alias", ch.get("remote_pubkey", "")[:12] + "..."),
            "capacity": int(ch.get("capacity", 0)),
            "local_balance": int(ch.get("local_balance", 0)),
            "remote_balance": int(ch.get("remote_balance", 0)),
            "fee_ppm": fee_lookup.get(ch.get("channel_point",""), {}).get("fee_ppm", 0),
            "base_fee": fee_lookup.get(ch.get("channel_point",""), {}).get("base_fee", 0),
            "channel_point": ch.get("channel_point", ""),
            "remote_pubkey": ch.get("remote_pubkey", ""),
            "chan_id": ch.get("chan_id", ""),
            "scid": str(ch.get("scid", "")),
            "initiator": ch.get("initiator", False),
            "status": "active" if ch.get("active") else "inactive",
        })
    return {
        "num_active": len([c for c in channel_list if c["status"] == "active"]),
        "num_inactive": len([c for c in channel_list if c["status"] == "inactive"]),
        "num_pending": len(pending.get("pending_open_channels", [])),
        "pending": [
            {
                "peer_alias": p.get("channel", {}).get("remote_node_pub", "Unknown")[:16] + "...",
                "capacity": int(p.get("channel", {}).get("capacity", 0)),
                "local_balance": int(p.get("channel", {}).get("local_balance", 0)),
                "channel_point": p.get("channel", {}).get("channel_point", ""),
                "status": "pending_open"
            }
            for p in pending.get("pending_open_channels", [])
        ],
        "total_capacity": sum(c["capacity"] for c in channel_list),
        "list": sorted(channel_list, key=lambda c: c["capacity"], reverse=True),
    }

@app.get("/api/routing")
def get_routing(days: int = 30):
    if MOCK:
        return MOCK_DATA["routing"]
    now_ts = int(time.time())
    start = now_ts - (days * 86400)
    history = run_lncli("fwdinghistory", f"--start_time={start}", "--max_events=1000")
    events = history.get("forwarding_events", [])
    start_60 = now_ts - (60 * 86400)
    history_60 = run_lncli("fwdinghistory", f"--start_time={start_60}", "--max_events=1000")
    events_60 = history_60.get("forwarding_events", [])
    start_all = now_ts - (365 * 86400)
    history_all = run_lncli("fwdinghistory", f"--start_time={start_all}", "--max_events=5000")
    events_all = history_all.get("forwarding_events", [])
    total_fees = sum(int(e.get("fee", 0)) for e in events)
    total_fees_60 = sum(int(e.get("fee", 0)) for e in events_60)
    total_fees_all = sum(int(e.get("fee", 0)) for e in events_all)
    total_vol = sum(int(e.get("amt_out", 0)) for e in events)
    daily_fees = [0] * 30
    daily_volume = [0] * 30
    from datetime import date
    today = date.today()
    for e in events:
        ts = int(e.get("timestamp", 0))
        event_date = date.fromtimestamp(ts)  # uses local time
        day = (today - event_date).days
        if 0 <= day < 30:
            idx = 29 - day
            daily_fees[idx] += int(e.get("fee", 0))
            daily_volume[idx] += int(e.get("amt_out", 0))
    # Build chan_id -> peer alias map
    channels = run_lncli("listchannels").get("channels", [])
    chan_map = {}
    for ch in channels:
        cid = ch.get("chan_id", "")
        alias = ch.get("peer_alias") or ch.get("remote_pubkey", "")[:12] + "..."
        if cid:
            chan_map[str(cid)] = alias

    # Enrich events with aliases
    def enrich(evts):
        out = []
        for e in evts:
            e2 = dict(e)
            e2["alias_in"]  = chan_map.get(str(e.get("chan_id_in",  "")), str(e.get("chan_id_in",  ""))[-8:])
            e2["alias_out"] = chan_map.get(str(e.get("chan_id_out", "")), str(e.get("chan_id_out", ""))[-8:])
            out.append(e2)
        return out

    return {
        "fees_30d_sats": total_fees,
        "fees_60d_sats": total_fees_60,
        "fees_alltime_sats": total_fees_all,
        "volume_30d_btc": round(total_vol / 100_000_000, 8),
        "forwarding_events": enrich(events_all),
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
    alias_cache = {ch.get("remote_pubkey"): ch.get("peer_alias", "Unknown") for ch in channels.get("channels", []) if ch.get("peer_alias")}
    peers = []
    for p in result.get("peers", []):
        pubkey = p.get("pub_key")
        peers.append({
            "pub_key": pubkey,
            "alias": alias_cache.get(p.get("pub_key", ""), "Unknown"),
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
        payments = run_lncli("listpayments", f"--max_payments={max(limit*10, 200) if limit > 0 else 2000}")
        NODE_PUBKEY = "03ee97ebe8b3e50c6272c3b33c7d730ad6722016ecb2d5fbfe9b0b7595383307d1"
        for p in payments.get("payments", []):
            if p.get("status") == "SUCCEEDED":
                # Detect circular rebalance — last hop is our own node
                is_rebalance = False
                try:
                    hops = p.get("htlcs", [{}])[0].get("route", {}).get("hops", [])
                    if hops and hops[-1].get("pub_key") == NODE_PUBKEY:
                        is_rebalance = True
                except:
                    pass
                transactions.append({
                    "type": "forwarded" if is_rebalance else "sent",
                    "amount": int(p.get("value_sat", 0)),
                    "fee": int(p.get("fee_sat", 0)),
                    "desc": "🔀 Channel rebalance (circular)" if is_rebalance else "Lightning payment sent",
                    "status": "confirmed",
                    "time": int(p.get("creation_date", 0))
                })
    except:
        pass

    # Get received invoices
    try:
        # Get newest invoices by finding total count first then using offset
        all_inv = run_lncli("listinvoices", "--max_invoices=1")
        total = int(all_inv.get("last_index_offset", 200))
        fetch_count = max(limit*10, 200) if limit > 0 else 2000
        offset = max(0, total - fetch_count)
        invoices = run_lncli("listinvoices", f"--max_invoices={fetch_count}", f"--index_offset={offset}", "--paginate-forwards")
        for inv in invoices.get("invoices", []):
            if inv.get("state") == "SETTLED":
                memo = inv.get("memo", "Lightning payment received")
                # Skip rebalance invoices — they show as sent already
                if "Auto-Rebalance" in memo or "Rebalance" in memo:
                    continue
                transactions.append({
                    "type": "received",
                    "amount": int(inv.get("amt_paid_sat", 0)),
                    "fee": 0,
                    "desc": memo,
                    "status": "confirmed",
                    "time": int(inv.get("settle_date", 0))
                })
    except:
        pass

    # Get on-chain transactions
    try:
        chaintxns = run_lncli("listchaintxns")
        for tx in chaintxns.get("transactions", []):
            amount = int(tx.get("amount", 0))
            if amount == 0:
                continue
            tx_type = "received" if amount > 0 else "sent"
            label = tx.get("label", "")
            if not label:
                label = "On-chain deposit" if amount > 0 else "On-chain payment"
            # Clean up ugly channel labels
            if "openchannel" in label: label = "Channel opened on-chain"
            if "closechannel" in label: label = "Channel closed on-chain"
            if "sweep" in label: label = "Channel sweep received"
            if label == "external": label = "On-chain payment"
            transactions.append({
                "type": tx_type,
                "amount": abs(amount),
                "fee": int(tx.get("total_fees", 0)),
                "desc": label,
                "status": "confirmed" if int(tx.get("num_confirmations", 0)) > 0 else "pending",
                "time": int(tx.get("time_stamp", 0)),
                "tx_hash": tx.get("tx_hash", ""),
                "num_confirmations": int(tx.get("num_confirmations", 0))
            })
    except:
        pass
    # Get routing fees
    try:
        fwd = run_lncli("fwdinghistory", "--max_events=5000")
        for e in fwd.get("forwarding_events", []):
            transactions.append({
                "type": "forwarded",
                "amount": int(e.get("amt_out", 0)),
                "fee": int(e.get("fee", 0)),
                "desc": "Routed {} → {}".format(
                    'Unknown' if not e.get('peer_alias_in') or 'lookup' in e.get('peer_alias_in','') or 'rpc' in e.get('peer_alias_in','') else e.get('peer_alias_in','').split(':')[0],
                    'Unknown' if not e.get('peer_alias_out') or 'lookup' in e.get('peer_alias_out','') or 'rpc' in e.get('peer_alias_out','') else e.get('peer_alias_out','').split(':')[0]
                ),
                "status": "confirmed",
                "time": int(e.get("timestamp", 0))
            })
    except:
        pass

    # Sort by time descending
    transactions.sort(key=lambda x: x["time"], reverse=True)
    # Apply limit AFTER sorting
    if limit > 0:
        transactions = transactions[:limit]
    # Convert unix timestamps to human readable
    now = time_module.time()
    for tx in transactions:
        t = tx["time"]
        diff = now - t
        if diff < 3600: tx["time"] = f"{int(diff/60)} min ago"
        elif diff < 86400: tx["time"] = f"{int(diff/3600)} hours ago"
        elif diff < 604800: tx["time"] = f"{int(diff/86400)} days ago"
        else: tx["time"] = datetime.fromtimestamp(t).strftime("%b %d %Y")
    
    return {"transactions": transactions}

@app.get("/api/system")
def get_system():
    import subprocess
    import threading, platform, socket
    
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
        {"name": "Bitcoin Core", "desc": "Full Bitcoin node — validates blocks and transactions", "unit": "bitcoin-core-rpc"},
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
            if svc["unit"] == "bitcoin-core-rpc":
                import requests as _req
                _user = os.getenv("RPC_USER", "")
                _pass = os.getenv("RPC_PASS", "")
                _host = os.getenv("RPC_HOST", "127.0.0.1")
                _port = os.getenv("RPC_PORT", "8332")
                _r = _req.post(f"http://{_host}:{_port}", json={"jsonrpc":"1.0","id":"ping","method":"getblockchaininfo","params":[]}, auth=(_user, _pass), timeout=3)
                svc["active"] = _r.status_code == 200
                svc["status"] = "active" if _r.status_code == 200 else "stopped"
            else:
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

@app.post("/api/openchannel")
@limiter.limit("3/minute")
def open_channel(request: Request, peer_address: str, local_amt: int, private: bool = False):
    if MOCK:
        return {"status": "mock"}
    try:
        # Extract pubkey from address
        pubkey = peer_address.split("@")[0]
        # Connect to peer first (ignore if already connected)
        try:
            run_lncli("connect", peer_address)
        except:
            pass  # Already connected is fine
        args = ["openchannel", f"--node_key={pubkey}", f"--local_amt={local_amt}"]
        if private:
            args.append("--private")
        result = run_lncli(*args)
        return {"status": "pending", "funding_txid": result.get("funding_txid", "")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/closechannel")
@limiter.limit("3/minute")
def close_channel(request: Request, chan_point: str, force: bool = False):
    if MOCK:
        return {"status": "mock"}
    try:
        txid, output = chan_point.split(":")
        args = ["closechannel", f"--funding_txid={txid}", f"--output_index={output}"]
        if force:
            args.append("--force")
        result = run_lncli(*args)
        return {"status": "closing", "txid": result.get("closing_txid", "pending")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chaninfo")
def get_chaninfo(scid: str = ""):
    if not scid:
        raise HTTPException(status_code=400, detail="scid required")
    result = run_lncli("getchaninfo", f"--chan_id={scid}")
    return result

@app.post("/api/sendpayment")
@limiter.limit("5/minute")
def send_payment(request: Request, body: dict = Body(...)):
    dest = body.get("dest", "")
    amount = body.get("amount", 0)
    if not dest:
        raise HTTPException(status_code=400, detail="Destination required")
    try:
        if dest.startswith("lnbc") or dest.startswith("lntb"):
            # Lightning invoice
            if amount > 0:
                result = run_lncli("sendpayment", "--pay_req=" + dest, "--amt=" + str(amount), "--json", "--force")
            else:
                result = run_lncli("sendpayment", "--pay_req=" + dest, "--json", "--force")
            if result.get("status") == "SUCCEEDED" or result.get("payment_hash"):
                return {"status": "success", "detail": "Lightning payment sent!", "fee": result.get("fee_sat", 0)}
            else:
                return {"status": "failed", "detail": result.get("failure_reason", "Payment failed")}
        elif dest.startswith("bc1") or dest.startswith("1") or dest.startswith("3"):
            # On-chain payment
            if amount <= 0:
                raise HTTPException(status_code=400, detail="Amount required for on-chain payments")
            result = run_lncli("sendcoins", "--addr=" + dest, "--amt=" + str(amount))
            return {"status": "success", "detail": "On-chain payment sent!", "txid": result.get("txid", "")}
        else:
            raise HTTPException(status_code=400, detail="Unrecognized payment destination")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/estimatefee")
def estimate_rebalance_fee(target_pubkey: str = "", amount: int = 0):
    if not target_pubkey:
        raise HTTPException(status_code=400, detail="target_pubkey required")
    if amount <= 0:
        data = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))
        amount = data.get("rebalance_amount", 50000)
    try:
        node_info = run_lncli("getinfo")
        my_pubkey = node_info.get("identity_pubkey", "")
        result = run_lncli("queryroutes", f"--dest={my_pubkey}", f"--amt={amount}")
        routes = result.get("routes", [])
        if routes:
            fee = int(routes[0].get("total_fees_msat", 0)) // 1000
            return {"status": "ok", "estimated_fee_sats": fee, "amount": amount, "hops": len(routes[0].get("hops", []))}
        return {"status": "no_route", "estimated_fee_sats": 0, "amount": amount, "detail": "No route found"}
    except Exception as e:
        return {"status": "error", "estimated_fee_sats": 0, "detail": str(e)}

@app.get("/api/feepolicy")
def get_fee_policy():
    if MOCK:
        return {"base_fee_msat": 1000, "fee_rate_ppm": 100, "time_lock_delta": 40}
    try:
        report = run_lncli("feereport")
        fees = report.get("channel_fees", [])
        if not fees:
            return {"base_fee_msat": 0, "fee_rate_ppm": 0, "time_lock_delta": 40}
        # Get most common fee across channels
        base = int(fees[0].get("base_fee_msat", 0))
        ppm = int(float(fees[0].get("fee_per_mil", 0)))
        return {"base_fee_msat": base, "fee_rate_ppm": ppm, "time_lock_delta": 40}
    except Exception as e:
        return {"base_fee_msat": 0, "fee_rate_ppm": 0, "time_lock_delta": 40}

@app.post("/api/updatefees")
def update_fees(base_fee_msat: int = 1000, fee_rate_ppm: int = 100, time_lock_delta: int = 40, chan_point: str = None):
    if MOCK:
        return {"status": "mock"}
    try:
        fee_rate = fee_rate_ppm / 1_000_000
        args = [
            "updatechanpolicy",
            f"--base_fee_msat={base_fee_msat}",
            f"--fee_rate={fee_rate}",
            f"--time_lock_delta={time_lock_delta}"
        ]
        if chan_point:
            args.append(f"--chan_point={chan_point}")
        result = run_lncli(*args)
        failed = result.get("failed_updates", [])
        return {"status": "done", "failed": len(failed), "message": f"Updated all channels — {len(failed)} failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rebalance")
def rebalance_channels(target_pubkey: str = None):
    if MOCK:
        return {"status": "mock", "message": "Rebalance simulated"}
    try:
        # Get all channels
        channels = run_lncli("listchannels")["channels"]
        results = []
        
        # Find overfull (>80%) and underfull (<20%) channels
        overfull = [c for c in channels if int(c["capacity"]) > 0 and 
                    int(c["local_balance"]) / int(c["capacity"]) > 0.80]
        underfull = [c for c in channels if int(c["capacity"]) > 0 and 
                     int(c["local_balance"]) / int(c["capacity"]) < 0.20]
        
        # If target_pubkey specified, only rebalance that channel
        if target_pubkey:
            target = [c for c in channels if c["remote_pubkey"] == target_pubkey]
            if target:
                ch = target[0]
                pct = int(ch["local_balance"]) / int(ch["capacity"])
                if pct > 0.50:
                    overfull = [ch]
                else:
                    underfull = [ch]
        
        if not overfull or not underfull:
            return {"status": "balanced", "message": "No rebalancing needed", "results": []}
        
        for src in overfull:
            for dst in underfull:
                src_cap = int(src["capacity"])
                src_local = int(src["local_balance"])
                dst_cap = int(dst["capacity"])
                dst_local = int(dst["local_balance"])
                
                # Calculate amount to rebalance (move toward 50%)
                settings = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))
                amount = min(
                    src_local - int(src_cap * 0.50),  # excess in source
                    int(dst_cap * 0.50) - dst_local,  # deficit in destination
                    int(settings.get("rebalance_amount", 50000))  # max per rebalance
                )
                
                if amount < 1000:
                    continue
                
                try:
                    # Get numeric chan_id for source channel via getchaninfo
                    src_chan_point = src.get("channel_point", "")
                    src_chan_id = None
                    if src_chan_point:
                        chan_info = run_lncli("getchaninfo", f"--chan_point={src_chan_point}")
                        src_chan_id = chan_info.get("channel_id")

                    # Create invoice to self
                    invoice = run_lncli("addinvoice", f"--amt={amount}", "--memo=LCC Auto-Rebalance")
                    payment_request = invoice.get("payment_request")

                    # Build sendpayment args with both source and destination control
                    pay_args = [
                        "sendpayment",
                        "--pay_req=" + payment_request,
                        "--last_hop=" + dst["remote_pubkey"],
                        "--allow_self_payment",
                        "--force",
                        "--timeout=30s",
                        "--json"
                    ]
                    if src_chan_id:
                        pay_args.append(f"--outgoing_chan_id={src_chan_id}")

                    result = run_lncli(*pay_args)
                    results.append({
                        "from": src.get("peer_alias", src["remote_pubkey"][:16]),
                        "to": dst.get("peer_alias", dst["remote_pubkey"][:16]),
                        "amount": amount,
                        "status": "success"
                    })
                except Exception as e:
                    results.append({
                        "from": src.get("peer_alias", src["remote_pubkey"][:16]),
                        "to": dst.get("peer_alias", dst["remote_pubkey"][:16]),
                        "amount": amount,
                        "status": "failed",
                        "error": str(e)
                    })
        
        return {"status": "done", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/rebalance")
def set_rebalance_schedule(hours: int = 24, amount: int = 50000):
    data = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))
    data["auto_rebalance_hours"] = hours
    data["rebalance_amount"] = amount
    with open(os.path.join(os.path.dirname(__file__), "data.json"), "w") as f:
        json.dump(data, f, indent=2)
    return {"auto_rebalance_hours": hours, "rebalance_amount": amount, "status": "updated"}

@app.get("/api/journal")
def get_journal():
    import os
    journal_path = os.path.join(os.path.dirname(__file__), "journal.json")
    try:
        with open(journal_path, "r") as f:
            return {"entries": json.load(f)}
    except:
        return {"entries": []}

@app.post("/api/journal")
def save_journal(request: Request):
    import asyncio, os
    journal_path = os.path.join(os.path.dirname(__file__), "journal.json")
    try:
        body = asyncio.run(request.json())
        entries = body.get("entries", [])
        with open(journal_path, "w") as f:
            json.dump(entries, f, indent=2)
        return {"status": "saved", "count": len(entries)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/lnbits")
def get_lnbits_settings():
    data = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))
    return {
        "url": data.get("lnbits_url", ""),
        "invoice_key": data.get("lnbits_invoice_key", "")
    }


@app.get("/api/pnl")
def get_pnl(period: str = "30d"):
    # Routing fees earned
    if period == "30d":
        days = 30
    elif period == "1y":
        days = 365
    else:
        days = 9999

    now_s = int(time.time())
    start_s = int(time.time() - days * 86400)

    if days >= 9999:
        history = run_lncli("fwdinghistory", "--start_time=1231006505", f"--end_time={now_s}", "--max_events=50000")
    else:
        history = run_lncli("fwdinghistory", f"--start_time={start_s}", f"--end_time={now_s}", "--max_events=50000")
    events = history.get("forwarding_events", []) if isinstance(history, dict) else []
    routing_fees = sum(int(e.get("fee", 0)) for e in events)

    # Rebalancing fees from wallet transactions
    txns = run_lncli("listpayments", "--max_payments=500")
    payments = txns.get("payments", []) if isinstance(txns, dict) else []
    rebalance_fees = sum(
        int(p.get("fee_sat", 0))
        for p in payments
        if p.get("status") == "SUCCEEDED" and p.get("payment_request", "").startswith("lnbc")
        and int(p.get("value_sat", 0)) > 0
    )

    # Channel opening fees (estimated from commit fees)
    channels = run_lncli("listchannels")
    open_fees = sum(int(c.get("commit_fee", 0)) for c in channels.get("channels", []))

    # Channel closing fees
    closed = run_lncli("closedchannels")
    close_fees = sum(int(c.get("close_fee_sat", 0)) for c in closed.get("channels", []))

    total_costs = rebalance_fees + open_fees + close_fees
    net_pnl = routing_fees - total_costs

    return {
        "period": period,
        "routing_fees": routing_fees,
        "rebalance_fees": rebalance_fees,
        "open_fees": open_fees,
        "close_fees": close_fees,
        "total_costs": total_costs,
        "net_pnl": net_pnl
    }

@app.get("/api/tier")
def get_tier():
    data = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))
    return {"tier": data.get("tier", "community")}

@app.post("/api/tier/{key}")
def set_tier(key: str):
    KEYS = {
        "LCC-PERSONAL-2025": "personal",
        "LCC-PRO-2025": "pro",
        "LCC-BETA-001-2026": "pro",
        "LCC-BETA-002-2026": "pro",
        "LCC-BETA-003-2026": "pro",
        "LCC-BETA-004-2026": "pro"
    }
    if key not in KEYS:
        raise HTTPException(status_code=403, detail="Invalid license key")
    data = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))
    data["tier"] = KEYS[key]
    with open(os.path.join(os.path.dirname(__file__), "data.json"), "w") as f:
        json.dump(data, f, indent=2)
    return {"tier": data["tier"], "status": "activated"}


# ─── NWC (Nostr Wallet Connect) ───────────────────────────────────────────────
import secrets
from nostr_sdk import Keys

NWC_RELAY = "wss://relay.primal.net"
NWC_DATA_FILE = os.path.join(os.path.dirname(__file__), "nwc_connections.json")

def load_nwc_data():
    if not os.path.exists(NWC_DATA_FILE):
        return {"connections": []}
    with open(NWC_DATA_FILE) as f:
        return json.load(f)

def save_nwc_data(data):
    with open(NWC_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.get("/api/nwc/connections")
def nwc_list_connections():
    data = load_nwc_data()
    return {"connections": data.get("connections", [])}

@app.post("/api/nwc/generate")
def nwc_generate(body: dict = Body(...)):
    name = body.get("name", "Unnamed App")
    permissions = body.get("permissions", ["pay_invoice", "get_balance"])
    budget_sats = body.get("budget_sats", 0)
    client_keys = Keys.generate()
    client_secret = client_keys.secret_key().to_hex()
    client_pubkey = client_keys.public_key().to_bech32()
    try:
        cfg = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))
        node_pubkey = cfg.get("nwc_pubkey_hex", cfg.get("nwc_pubkey", ""))
    except:
        node_pubkey = ""
    nwc_uri = f"nostr+walletconnect://{node_pubkey}?relay={NWC_RELAY}&secret={client_secret}"
    conn = {
        "id": secrets.token_hex(8),
        "name": name,
        "permissions": permissions,
        "budget_sats": budget_sats,
        "client_pubkey": client_pubkey,
        "created_at": int(time.time()),
        "last_used": None,
        "active": True,
        "nwc_uri": nwc_uri
    }
    data = load_nwc_data()
    data["connections"].append(conn)
    save_nwc_data(data)
    return {"connection": conn, "nwc_uri": nwc_uri}

@app.post("/api/nwc/revoke")
def nwc_revoke(body: dict = Body(...)):
    conn_id = body.get("id")
    data = load_nwc_data()
    for c in data["connections"]:
        if c["id"] == conn_id:
            c["active"] = False
    save_nwc_data(data)
    return {"status": "revoked"}

@app.delete("/api/nwc/connection/{conn_id}")
def nwc_delete(conn_id: str):
    data = load_nwc_data()
    data["connections"] = [c for c in data["connections"] if c["id"] != conn_id]
    save_nwc_data(data)
    return {"status": "deleted"}

@app.post("/api/auth/verify-password")
def verify_password(body: dict = Body(...)):
    pw = body.get("password", "")
    cfg = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))
    correct = cfg.get("lcc_password", "")
    return {"authorized": pw == correct}

@app.post("/api/nostr/verify-nsec")
def verify_nsec(body: dict = Body(...)):
    from nostr_sdk import SecretKey, Keys
    try:
        nsec = body.get("nsec", "")
        sk = SecretKey.parse(nsec)
        keys = Keys(sk)
        pubkey_hex = keys.public_key().to_hex()
        cfg = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))
        node_pubkey = cfg.get("nwc_pubkey_hex", "")
        authorized = pubkey_hex == node_pubkey
        return {"authorized": authorized}
    except Exception as e:
        return {"authorized": False, "error": str(e)}


# ─── Drain & Trap Channel Strategy ───────────────────────────────────────────
@app.get("/api/channel-strategies")
def get_channel_strategies():
    data = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))
    return {"strategies": data.get("channel_strategies", {})}

@app.post("/api/channel-strategies/{chan_point:path}")
def set_channel_strategy(chan_point: str, body: dict = Body(...)):
    f = os.path.join(os.path.dirname(__file__), "data.json")
    data = json.load(open(f))
    if "channel_strategies" not in data:
        data["channel_strategies"] = {}
    strategy = body.get("strategy", "balanced")
    if strategy == "none":
        data["channel_strategies"].pop(chan_point, None)
    else:
        data["channel_strategies"][chan_point] = {
            "strategy": strategy,
            "drain_ppm": body.get("drain_ppm", 50),
            "trap_ppm": body.get("trap_ppm", 1200),
            "floor_pct": body.get("floor_pct", 2),
            "state": "draining",
            "set_at": int(time.time())
        }
    with open(f, "w") as file:
        json.dump(data, file, indent=2)
    return {"status": "saved", "strategy": data["channel_strategies"].get(chan_point)}

# Auto-rebalance scheduler
def auto_rebalance_job():
    while True:
        try:
            settings = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))
            hours = int(settings.get("auto_rebalance_hours", 24))
            if hours > 0 and not MOCK:
                channels = run_lncli("listchannels")["channels"]
                overfull = [c for c in channels if int(c["capacity"]) > 0 and
                            int(c["local_balance"]) / int(c["capacity"]) > 0.80]
                underfull = [c for c in channels if int(c["capacity"]) > 0 and
                             int(c["local_balance"]) / int(c["capacity"]) < 0.20]
                if overfull and underfull:
                    rebalance_channels()
                wait = hours * 3600
            else:
                wait = 3600
        except:
            wait = 86400
        threading.Event().wait(wait)

def drain_trap_worker():
    while True:
        try:
            data = json.load(open(os.path.join(os.path.dirname(__file__), "data.json")))
            strategies = data.get("channel_strategies", {})
            if strategies and not MOCK:
                channels = run_lncli("listchannels").get("channels", [])
                for ch in channels:
                    chan_point = ch.get("channel_point", "")
                    s = strategies.get(chan_point)
                    if not s or s.get("strategy") != "drain_trap":
                        continue
                    cap = int(ch.get("capacity", 1))
                    local = int(ch.get("local_balance", 0))
                    pct = (local / cap) * 100
                    floor = s.get("floor_pct", 2)
                    drain_ppm = s.get("drain_ppm", 50)
                    trap_ppm = s.get("trap_ppm", 1200)
                    current_state = s.get("state", "draining")
                    if pct <= floor and current_state != "trapped":
                        # Switch to trap mode
                        run_lncli("updatechanpolicy",
                            f"--base_fee_msat=0",
                            f"--fee_rate_ppm={trap_ppm}",
                            "--time_lock_delta=40",
                            f"--chan_point={chan_point}")
                        strategies[chan_point]["state"] = "trapped"
                        strategies[chan_point]["trapped_at"] = int(time.time())
                        data["channel_strategies"] = strategies
                        with open(os.path.join(os.path.dirname(__file__), "data.json"), "w") as f:
                            json.dump(data, f, indent=2)
                    elif pct > floor and current_state == "trapped":
                        # Back to drain mode
                        run_lncli("updatechanpolicy",
                            f"--base_fee_msat=0",
                            f"--fee_rate_ppm={drain_ppm}",
                            "--time_lock_delta=40",
                            f"--chan_point={chan_point}")
                        strategies[chan_point]["state"] = "draining"
                        data["channel_strategies"] = strategies
                        with open(os.path.join(os.path.dirname(__file__), "data.json"), "w") as f:
                            json.dump(data, f, indent=2)
        except Exception as e:
            pass
        threading.Event().wait(300)  # Check every 5 minutes

drain_trap_thread = threading.Thread(target=drain_trap_worker, daemon=True)
drain_trap_thread.start()

scheduler_thread = threading.Thread(target=auto_rebalance_job, daemon=True)
scheduler_thread.start()
