import subprocess
import threading
import json
import os
from dotenv import load_dotenv
load_dotenv()

# Data files live under LCC_DATA_DIR when set (a mounted volume on StartOS or
# Umbrel, so they survive image upgrades); otherwise this script's own
# directory, which is what bare-metal installs like the ProDesk have always
# used. Unset means identical behaviour to before.
LCC_DATA_DIR = os.environ.get("LCC_DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
_DATA_JSON_PATH = os.path.join(LCC_DATA_DIR, "data.json")
# A fresh install has no data.json yet; create an empty one so every place
# that reads it works from the very first start (StartOS, Umbrel, Docker).
try:
    os.makedirs(LCC_DATA_DIR, exist_ok=True)
    if not os.path.exists(_DATA_JSON_PATH):
        with open(_DATA_JSON_PATH, "w") as _f:
            _f.write("{}")
except Exception as _e:
    print(f"[lcc] warning: could not create {_DATA_JSON_PATH}: {_e}")
import time
from datetime import datetime, timezone
import time as time_module
import requests
import base64
from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

def _read_lcc_version():
    """The release number lives in one place: the VERSION file next to this script."""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")) as _vf:
            return _vf.read().strip() or "dev"
    except Exception:
        return "dev"


LCC_VERSION = _read_lcc_version()
app = FastAPI(title="Lightning Control Center API", version=LCC_VERSION)
app.state.limiter = limiter

from slowapi.middleware import SlowAPIMiddleware
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("LCC_CORS_ORIGINS", "https://lcc.satslist.shop,http://localhost:8765").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK = os.environ.get("LCC_MOCK", "false").lower() == "true"

MOCK_DATA = json.load(open(_DATA_JSON_PATH)) if MOCK else {}

# ─── LND REST connection (v0.2.0 — remote node connection) ───────────────────
# Replaces the old `lncli` subprocess wrapper. Works identically whether LND
# is co-located (ProDesk, litd on localhost) or remote (e.g. LND packaged on
# StartOS reached over the network) — same REST API, just a different host.
# Configure via .env:
#   LND_REST_HOST=https://127.0.0.1:8080         (default — local litd)
#   LND_MACAROON_PATH=~/.lnd/data/chain/bitcoin/mainnet/admin.macaroon
#   LND_TLS_CERT_PATH=~/.lnd/tls.cert
#   LND_TLS_INSECURE=true                         (only if cert can't be verified, e.g. IP-based remote)
LND_REST_HOST = os.getenv("LND_REST_HOST", "https://127.0.0.1:8080").rstrip("/")
LND_MACAROON_PATH = os.path.expanduser(os.getenv(
    "LND_MACAROON_PATH", "~/.lnd/data/chain/bitcoin/mainnet/admin.macaroon"
))
LND_TLS_CERT_PATH = os.path.expanduser(os.getenv("LND_TLS_CERT_PATH", "~/.lnd/tls.cert"))
LND_TLS_INSECURE = os.getenv("LND_TLS_INSECURE", "false").lower() == "true"


def _lnd_macaroon_hex():
    try:
        with open(LND_MACAROON_PATH, "rb") as f:
            return f.read().hex()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"LND macaroon not found at {LND_MACAROON_PATH}")


def _lnd_verify():
    if LND_TLS_INSECURE:
        return False
    if os.path.exists(LND_TLS_CERT_PATH):
        return LND_TLS_CERT_PATH
    return True  # fall back to system CA bundle (e.g. behind a reverse proxy with a real cert)


def _lnd_rest(method, path, params=None, body=None, timeout=10):
    """Single (non-streaming) call to LND's REST API. Raises HTTPException on
    failure — same contract the old subprocess-based run_lncli() had, so every
    existing caller's try/except HTTPException handling keeps working."""
    try:
        resp = requests.request(
            method, f"{LND_REST_HOST}{path}",
            headers={"Grpc-Metadata-macaroon": _lnd_macaroon_hex()},
            params={k: v for k, v in (params or {}).items() if v is not None},
            json=body, timeout=timeout, verify=_lnd_verify(),
        )
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="LND REST call timed out")
    except requests.exceptions.ConnectionError as e:
        raise HTTPException(status_code=500, detail=f"Can't reach LND at {LND_REST_HOST} — is it running? ({e})")
    if resp.status_code != 200:
        try:
            detail = resp.json().get("message", resp.text)
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=500, detail=f"LND error: {detail.strip()}")
    try:
        return resp.json()
    except ValueError:
        return {}


def _lnd_rest_stream_first(method, path, params=None, body=None, timeout=30):
    """For LND's streaming endpoints (openchannel, closechannel) where we only
    need the first update — the point at which the funding/closing txid is
    known — matching how `lncli openchannel`/`closechannel` used to block."""
    try:
        with requests.request(
            method, f"{LND_REST_HOST}{path}",
            headers={"Grpc-Metadata-macaroon": _lnd_macaroon_hex()},
            params={k: v for k, v in (params or {}).items() if v is not None},
            json=body, timeout=timeout, verify=_lnd_verify(), stream=True,
        ) as resp:
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail=f"LND error: {resp.text.strip()}")
            for line in resp.iter_lines():
                if not line:
                    continue
                obj = json.loads(line)
                if "error" in obj:
                    raise HTTPException(status_code=500, detail=str(obj["error"]))
                return obj.get("result", obj)
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="LND REST stream timed out")
    except requests.exceptions.ConnectionError as e:
        raise HTTPException(status_code=500, detail=f"Can't reach LND at {LND_REST_HOST} ({e})")
    raise HTTPException(status_code=500, detail="LND returned no data")


def _lnd_rest_stream_terminal(method, path, params=None, body=None, timeout=90):
    """For SendPaymentV2 (/v2/router/send) — read status updates until the
    payment reaches a terminal state (SUCCEEDED/FAILED), the way
    `lncli sendpayment` blocks until the payment resolves."""
    try:
        with requests.request(
            method, f"{LND_REST_HOST}{path}",
            headers={"Grpc-Metadata-macaroon": _lnd_macaroon_hex()},
            params={k: v for k, v in (params or {}).items() if v is not None},
            json=body, timeout=timeout, verify=_lnd_verify(), stream=True,
        ) as resp:
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail=f"LND error: {resp.text.strip()}")
            last = {}
            for line in resp.iter_lines():
                if not line:
                    continue
                obj = json.loads(line)
                if "error" in obj:
                    raise HTTPException(status_code=500, detail=str(obj["error"]))
                last = obj.get("result", obj)
                if last.get("status") in ("SUCCEEDED", "FAILED"):
                    return last
            return last
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Payment timed out")
    except requests.exceptions.ConnectionError as e:
        raise HTTPException(status_code=500, detail=f"Can't reach LND at {LND_REST_HOST} ({e})")


def _parse_flags(args):
    """Mini lncli-style arg parser: turns ('--amt=100', '--force', 'p2wkh')
    into ({'amt': '100', 'force': True}, ['p2wkh'])."""
    flags, positional = {}, []
    for a in args:
        if a.startswith("--"):
            if "=" in a:
                k, v = a[2:].split("=", 1)
                flags[k] = v
            else:
                flags[a[2:]] = True
        else:
            positional.append(a)
    return flags, positional


def _resolve_chan_id(chan_point):
    """getchaninfo only takes a numeric chan_id over REST — some call sites in
    this file pass --chan_point instead (a pre-existing bug that silently
    no-op'd under the old lncli subprocess wrapper). Resolve it transparently
    instead of failing."""
    channels = _lnd_rest("GET", "/v1/channels").get("channels", [])
    for ch in channels:
        if ch.get("channel_point") == chan_point:
            return ch.get("chan_id")
    return None


def run_lncli(*args):
    """Drop-in replacement for the old subprocess-based run_lncli() — same
    call signature (run_lncli("getinfo"), run_lncli("sendpayment", "--pay_req=...", ...)),
    now translated to LND's REST API instead of shelling out to the `lncli`
    binary. Every one of this file's ~80 run_lncli(...) call sites is
    unchanged below this function."""
    if not args:
        raise HTTPException(status_code=500, detail="run_lncli called with no command")
    cmd = args[0]
    flags, positional = _parse_flags(args[1:])

    try:
        if cmd == "getinfo":
            return _lnd_rest("GET", "/v1/getinfo")

        if cmd == "walletbalance":
            r = _lnd_rest("GET", "/v1/balance/blockchain")
            return {
                "total_balance": r.get("total_balance", "0"),
                "confirmed_balance": r.get("confirmed_balance", "0"),
                "unconfirmed_balance": r.get("unconfirmed_balance", "0"),
            }

        if cmd == "channelbalance":
            r = _lnd_rest("GET", "/v1/balance/channels")
            return {"balance": r.get("local_balance", {}).get("sat", "0")}

        if cmd == "listchannels":
            r = _lnd_rest("GET", "/v1/channels", params={"peer_alias_lookup": True})
            channels = r.get("channels", [])
            alias_cache = {}
            for ch in channels:
                ch.setdefault("scid", ch.get("chan_id"))
                if not ch.get("peer_alias"):
                    pubkey = ch.get("remote_pubkey", "")
                    if pubkey not in alias_cache:
                        try:
                            node = _lnd_rest("GET", f"/v1/graph/node/{pubkey}", params={"include_channels": False})
                            alias_cache[pubkey] = node.get("node", {}).get("alias", "")
                        except HTTPException:
                            alias_cache[pubkey] = ""
                    if alias_cache[pubkey]:
                        ch["peer_alias"] = alias_cache[pubkey]
            return r

        if cmd == "pendingchannels":
            return _lnd_rest("GET", "/v1/channels/pending")

        if cmd == "closedchannels":
            return _lnd_rest("GET", "/v1/channels/closed")

        if cmd == "feereport":
            return _lnd_rest("GET", "/v1/fees")

        if cmd == "fwdinghistory":
            body = {
                "start_time": str(flags.get("start_time", "0")),
                "end_time": str(flags.get("end_time", str(int(time.time())))),
                "num_max_events": int(flags.get("max_events", 100)),
                "index_offset": int(flags.get("index_offset", 0)),
                # Ask LND to resolve peer aliases; without this it returns bare
                # channel IDs and the routing page has no names to show.
                "peer_alias_lookup": True,
            }
            return _lnd_rest("POST", "/v1/switch", body=body)

        if cmd == "listpeers":
            return _lnd_rest("GET", "/v1/peers")

        if cmd == "listpayments":
            params = {
                "max_payments": flags.get("max_payments"),
                "index_offset": flags.get("index_offset"),
                "reversed": "paginate-forwards" not in flags and "paginate_forwards" not in flags,
                "include_incomplete": True,
            }
            return _lnd_rest("GET", "/v1/payments", params=params)

        if cmd == "listinvoices":
            params = {
                "num_max_invoices": flags.get("max_invoices"),
                "index_offset": flags.get("index_offset"),
                "reversed": "paginate-forwards" not in flags,
            }
            return _lnd_rest("GET", "/v1/invoices", params=params)

        if cmd == "listchaintxns":
            return _lnd_rest("GET", "/v1/transactions")

        if cmd == "newaddress":
            addr_type = "WITNESS_PUBKEY_HASH" if (not positional or positional[0] == "p2wkh") else positional[0]
            return _lnd_rest("GET", "/v1/newaddress", params={"type": addr_type})

        if cmd == "connect":
            addr = positional[0] if positional else flags.get("addr")
            pubkey, _, host = addr.partition("@")
            body = {"addr": {"pubkey": pubkey, "host": host}, "perm": False}
            try:
                return _lnd_rest("POST", "/v1/peers", body=body)
            except HTTPException as e:
                if "already connected" in str(e.detail).lower():
                    return {"status": "already connected"}
                raise

        if cmd == "getnodeinfo":
            pubkey = flags.get("pub_key") or (positional[0] if positional else "")
            return _lnd_rest("GET", f"/v1/graph/node/{pubkey}", params={"include_channels": False})

        if cmd == "getchaninfo":
            chan_id = flags.get("chan_id")
            if not chan_id and flags.get("chan_point"):
                chan_id = _resolve_chan_id(flags["chan_point"])
            if not chan_id and positional:
                chan_id = positional[0]
            if not chan_id:
                raise HTTPException(status_code=400, detail="getchaninfo needs a chan_id or a matching chan_point")
            return _lnd_rest("GET", f"/v1/graph/edge/{chan_id}")

        if cmd == "queryroutes":
            dest = flags.get("dest")
            amt = flags.get("amt")
            return _lnd_rest("GET", f"/v1/graph/routes/{dest}/{amt}")

        if cmd == "addinvoice":
            body = {"value": str(flags.get("amt", "0")), "memo": flags.get("memo", "")}
            r = _lnd_rest("POST", "/v1/invoices", body=body)
            return {
                "payment_request": r.get("payment_request"),
                "r_hash": r.get("r_hash"),
                "add_index": r.get("add_index"),
            }

        if cmd == "sendpayment":
            timeout_seconds = int(str(flags.get("timeout", "60s")).rstrip("s") or 60)
            body = {
                "payment_request": flags.get("pay_req"),
                "allow_self_payment": "allow_self_payment" in flags,
                "timeout_seconds": timeout_seconds,
            }
            if flags.get("amt"):
                body["amt"] = str(flags["amt"])
            if flags.get("fee_limit"):
                body["fee_limit_sat"] = str(flags["fee_limit"])
            if flags.get("outgoing_chan_id"):
                body["outgoing_chan_ids"] = [str(flags["outgoing_chan_id"])]
            if flags.get("last_hop"):
                body["last_hop_pubkey"] = base64.b64encode(bytes.fromhex(flags["last_hop"])).decode()
            payment = _lnd_rest_stream_terminal(
                "POST", "/v2/router/send", body=body, timeout=timeout_seconds + 15
            )
            if payment.get("status") == "SUCCEEDED":
                fee_msat = int(payment.get("fee_msat", 0) or 0)
                return {"status": "SUCCEEDED", "fee_sat": fee_msat // 1000, "payment_hash": payment.get("payment_hash")}
            return {"status": "FAILED", "failure_reason": payment.get("failure_reason", "FAILURE_REASON_ERROR")}

        if cmd == "sendcoins":
            body = {"addr": flags.get("addr"), "amount": str(flags.get("amt", "0"))}
            r = _lnd_rest("POST", "/v1/transactions", body=body)
            return {"txid": r.get("txid")}

        if cmd == "openchannel":
            node_key = flags.get("node_key")
            body = {
                "node_pubkey": base64.b64encode(bytes.fromhex(node_key)).decode(),
                "local_funding_amount": str(flags.get("local_amt", "0")),
                "private": "private" in flags,
            }
            first = _lnd_rest_stream_first("POST", "/v1/channels", body=body, timeout=60)
            chan_pending = first.get("chan_pending", {}) or {}
            txid_b64 = chan_pending.get("txid")
            txid = base64.b64decode(txid_b64)[::-1].hex() if txid_b64 else ""
            return {"funding_txid": txid}

        if cmd == "closechannel":
            txid = flags.get("funding_txid")
            idx = flags.get("output_index", "0")
            params = {"force": "force" in flags}
            first = _lnd_rest_stream_first("DELETE", f"/v1/channels/{txid}/{idx}", params=params, timeout=60)
            close_pending = first.get("close_pending", {}) or {}
            txid_b64 = close_pending.get("txid")
            closing_txid = base64.b64decode(txid_b64)[::-1].hex() if txid_b64 else "pending"
            return {"closing_txid": closing_txid}

        if cmd == "updatechanpolicy":
            base_fee = int(flags.get("base_fee_msat", 0))
            if "fee_rate_ppm" in flags:
                ppm = int(flags["fee_rate_ppm"])
            else:
                ppm = int(round(float(flags.get("fee_rate", 0)) * 1_000_000))
            body = {
                "base_fee_msat": str(base_fee),
                "fee_rate_ppm": ppm,  # LND rejects the request if both this and the legacy `fee_rate` are set
                "time_lock_delta": int(flags.get("time_lock_delta", 40)),
            }
            if flags.get("chan_point"):
                txid, _, idx = flags["chan_point"].partition(":")
                body["chan_point"] = {"funding_txid_str": txid, "output_index": int(idx)}
            else:
                body["global"] = True
            r = _lnd_rest("POST", "/v1/chanpolicy", body=body)
            return {"failed_updates": r.get("failed_updates", [])}

        raise HTTPException(status_code=500, detail=f"lncli command '{cmd}' has no REST translation yet")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LND REST translation error for '{cmd}': {e}")


# Configurable so a container can point at its own binary, or none at all,
# instead of assuming the ProDesk's snap install.
BITCOIN_CLI_PATH = os.getenv("BITCOIN_CLI_PATH", "/snap/bitcoin-core/current/bin/bitcoin-cli")

# --- Optional, machine-specific features: off unless set in .env ------------
import shutil as _shutil
import socket as _socket
import re as _re_ff
LCC_MINING_ENABLED = os.getenv("LCC_MINING_ENABLED", "") == "1"
LCC_LIVE_STREAM_URL = os.getenv("LCC_LIVE_STREAM_URL", "").strip()
LCC_POOL_URL = os.getenv("LCC_POOL_URL", "").strip()
# Host services (systemctl) exist on bare-metal installs like the ProDesk, not
# inside a StartOS/Umbrel container, where the node OS manages services.
_HOST_SERVICES = _shutil.which("systemctl") is not None and os.getenv("LCC_HIDE_HOST_SERVICES", "") != "1"
_ext_ip_cache = {"t": 0.0, "ip": None}


def _local_ip():
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s.connect(("192.0.2.1", 9))  # no packet is sent; just picks the outgoing interface
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def _external_ip():
    now = time.time()
    if now - _ext_ip_cache["t"] > 600:
        try:
            _ext_ip_cache["ip"] = requests.get("https://api.ipify.org", timeout=5).text.strip() or None
        except Exception:
            _ext_ip_cache["ip"] = None
        _ext_ip_cache["t"] = now
    return _ext_ip_cache["ip"]


def _apply_feature_flags(html):
    """Drop nav/palette entries for features this machine doesn't have."""
    out = []
    for line in html.split("\n"):
        if ('data-feature="livestream"' in line or "/*lcc:livestream*/" in line) and not LCC_LIVE_STREAM_URL:
            continue
        if ('data-feature="mining"' in line or "/*lcc:mining*/" in line) and not LCC_MINING_ENABLED:
            continue
        out.append(line)
    safe_url = _re_ff.sub(r"[^A-Za-z0-9:/._?=&%#-]", "", LCC_LIVE_STREAM_URL)
    return "\n".join(out).replace("__LCC_LIVE_STREAM_URL__", safe_url)
_bitcoin_cli_warned = False


def _warn_bitcoin_once(msg):
    global _bitcoin_cli_warned
    if not _bitcoin_cli_warned:
        print(f"[lcc] {msg} - Bitcoin Core data will be omitted")
        _bitcoin_cli_warned = True


def run_bitcoin_cli(*args):
    """Query Bitcoin Core, returning {} when it is not reachable.

    Bitcoin Core is optional: LCC may run in a container without it, or
    against a remote LND. Callers all use .get() with defaults, so an empty
    result blanks those individual fields rather than failing the whole
    request - which otherwise takes the entire dashboard down with it.
    """
    try:
        rpc_user = os.getenv("RPC_USER", "")
        rpc_pass = os.getenv("RPC_PASS", "")
        result = subprocess.run([BITCOIN_CLI_PATH, f"-rpcuser={rpc_user}", f"-rpcpassword={rpc_pass}"] + list(args), capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            _warn_bitcoin_once(f"bitcoin-cli error: {result.stderr.strip()}")
            return {}
        return json.loads(result.stdout)
    except FileNotFoundError:
        _warn_bitcoin_once(f"bitcoin-cli not found at {BITCOIN_CLI_PATH}")
        return {}
    except subprocess.TimeoutExpired:
        _warn_bitcoin_once("bitcoin-cli timed out")
        return {}
    except Exception as e:
        _warn_bitcoin_once(f"bitcoin-cli unavailable: {e}")
        return {}

@app.get("/")
def root():
        return RedirectResponse(url="/dashboard")

@app.get("/api/node")
def get_node_info():
    if MOCK:
        return MOCK_DATA["node"]
    info = run_lncli("getinfo")
    return {
        "alias": info.get("alias"),
        "pubkey": info.get("identity_pubkey"),
        "version": info.get("version"),
        "uris": info.get("uris", []),
        "status": "online",
        "synced_to_chain": info.get("synced_to_chain"),
        "synced_to_graph": info.get("synced_to_graph"),
        "block_height": info.get("block_height"),
        "num_peers": info.get("num_peers"),
        "uptime_seconds": int(__import__("time").time() - __import__("psutil").boot_time()),
        "auto_rebalance_hours": json.load(open(_DATA_JSON_PATH)).get("auto_rebalance_hours", 24),
        "rebalance_amount": json.load(open(_DATA_JSON_PATH)).get("rebalance_amount", 50000),
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
    history = run_lncli("fwdinghistory", f"--start_time={start}", "--max_events=5000")
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
        alias = ch.get("peer_alias") or ch.get("remote_pubkey", "")[:12] + "..."
        # Map both numeric chan_id and scid to alias
        for key in ["chan_id", "scid"]:
            cid = ch.get(key, "")
            if cid:
                chan_map[str(cid)] = alias

    # Add closed channels — forwarding history includes events through channels
    # that may now be closed, so we need them in the alias map too
    try:
        _closed = _lnd_rest("GET", "/v1/channels/closed").get("channels", [])
        print(f"CLOSED_CHAN_DEBUG: found {len(_closed)} closed channels", flush=True)
        _watch = {"1057623533383516161","1057766469876318209","1057764270845853697","1058350310578454529"}
        for _dbg in _closed:
            if str(_dbg.get("chan_id","")) in _watch:
                print(f"CLOSED_CHAN_DEBUG: MATCH chan_id={_dbg.get('chan_id')} pk={_dbg.get('remote_pubkey','')[:20]}", flush=True)
        _pub_alias: dict = {}
        for _ch in _closed:
            _cid = str(_ch.get("chan_id", ""))
            if _cid and _cid not in chan_map:
                _pk = _ch.get("remote_pubkey", "")
                if _pk:
                    if _pk not in _pub_alias:
                        try:
                            _n = _lnd_rest("GET", f"/v1/graph/node/{_pk}",
                                          params={"include_channels": False})
                            _pub_alias[_pk] = _n.get("node", {}).get("alias", "") or _pk[:12] + "..."
                        except Exception:
                            _pub_alias[_pk] = _pk[:12] + "..."
                    chan_map[_cid] = _pub_alias[_pk]
    except Exception:
        pass  # best-effort; must not break the routing page

    # Build alias -> current fee policy (base_msat + ppm) of the OUTBOUND channel,
    # since that's the leg that actually charges the fee for a routed payment
    fee_report = run_lncli("feereport").get("channel_fees", [])
    fee_policy = {}
    for fr in fee_report:
        cid = str(fr.get("chan_id", ""))
        alias = chan_map.get(cid, cid[-8:] if cid else "?")
        fee_policy[alias] = {
            "base_msat": int(fr.get("base_fee_msat", 0)),
            "ppm": int(fr.get("fee_per_mil", 0)),
        }

    # Enrich events with aliases
    def enrich(evts):
        out = []
        for e in evts:
            e2 = dict(e)
            _cii = str(e.get("chan_id_in",  ""))
            _cio = str(e.get("chan_id_out", ""))
            e2["alias_in"]  = chan_map.get(_cii, _cii[-8:] if _cii else "?")
            e2["alias_out"] = chan_map.get(_cio, _cio[-8:] if _cio else "?")
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
        "fee_policy": fee_policy,
    }


@app.get("/api/ip-check")
def check_ip_match():
    """Check if the advertised externalip matches the current public IP"""
    try:
        import urllib.request
        current_ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode().strip()
    except:
        current_ip = None
    
    advertised_ip = None
    try:
        with open(os.path.expanduser("~/.lnd/lnd.conf")) as f:
            for line in f:
                if line.strip().startswith("externalip="):
                    advertised_ip = line.strip().split("=", 1)[1].split(":")[0]
                    break
    except:
        pass
    
    match = (current_ip == advertised_ip) if (current_ip and advertised_ip) else None
    
    return {
        "current_ip": current_ip,
        "advertised_ip": advertised_ip,
        "match": match
    }

@app.post("/api/ip-fix")
def fix_ip():
    """Update lnd.conf externalip to match current public IP and restart LND"""
    try:
        import urllib.request, subprocess
        current_ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode().strip()
        
        conf_path = os.path.expanduser("~/.lnd/lnd.conf")
        with open(conf_path) as f:
            lines = f.readlines()
        
        new_lines = []
        updated = False
        for line in lines:
            if line.strip().startswith("externalip="):
                port = line.strip().split(":")[-1] if ":" in line.strip() else "9735"
                new_lines.append(f"externalip={current_ip}:{port}\n")
                updated = True
            else:
                new_lines.append(line)
        
        if updated:
            with open(conf_path, "w") as f:
                f.writelines(new_lines)
            
            subprocess.run(["sudo", "systemctl", "restart", "lnd"], check=True)
            _log_journal(
                "IP Address Updated",
                f"Node externalip updated to {current_ip} and LND restarted.",
                "system"
            )
            return {"status": "success", "new_ip": current_ip}
        else:
            return {"status": "error", "detail": "No externalip line found in lnd.conf"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/api/mempool")
def get_mempool():
    if MOCK:
        return MOCK_DATA["mempool"]
    info = run_bitcoin_cli("getmempoolinfo")
    if info and "bytes" in info:
        size_mb = round(info.get("bytes", 0) / 1_000_000, 1)
    else:
        # No Bitcoin Core connection (e.g. StartOS/Umbrel) - use mempool.space,
        # which this endpoint already relies on for fee rates.
        size_mb = None
        try:
            _mp = requests.get("https://mempool.space/api/mempool", timeout=5).json()
            size_mb = round(int(_mp.get("vsize", 0)) / 1_000_000, 1)
        except Exception:
            pass
    
    # Use mempool.space API for accurate real-time fee rates
    try:
        import urllib.request
        req = urllib.request.urlopen("https://mempool.space/api/v1/fees/recommended", timeout=5)
        fees = json.loads(req.read().decode())
        fee_sat_vbyte = fees.get("halfHourFee", 1)
    except:
        # Fallback to Bitcoin Core estimate
        fee_info = run_bitcoin_cli("estimatesmartfee", "6")
        fee_sat_vbyte = round(fee_info.get("feerate", 0.00001) * 100_000_000 / 1000, 1)
    
    if size_mb is None:
        return {"size_mb": 0, "fee_sat_vbyte": fee_sat_vbyte, "congestion": "Unknown"}
    congestion = "Low" if size_mb < 5 else "Medium" if size_mb < 50 else "High"
    return {"size_mb": size_mb, "fee_sat_vbyte": fee_sat_vbyte, "congestion": congestion}

@app.get("/api/mining")
def get_mining():
    if MOCK:
        return MOCK_DATA["mining"]
    return {"miners": [], "total_hashrate": 0, "status": "not configured"}

@app.get("/api/features")
def get_features():
    return {
        "mining": LCC_MINING_ENABLED,
        "live_stream_url": LCC_LIVE_STREAM_URL,
        "pool_url": LCC_POOL_URL,
        "host_services": _HOST_SERVICES,
    }

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
        NODE_PUBKEY = (run_lncli("getinfo") or {}).get("identity_pubkey", "")
        # Build pubkey to alias map
        alias_map = {ch.get("remote_pubkey",""): ch.get("peer_alias","") for ch in run_lncli("listchannels").get("channels", [])}
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
                    "desc": ("🔀 Rebalance: " + alias_map.get(hops[0].get("pub_key",""), hops[0].get("pub_key","")[:12]) + " → " + alias_map.get(hops[-2].get("pub_key",""), hops[-2].get("pub_key","")[:12]) if len(hops) >= 2 else "🔀 Channel rebalance (circular)") if is_rebalance else "Lightning payment sent",
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
            if "BatchOutSweepSuccess" in label: label = "🔄 Loop Out sweep"
            if "BatchInSweepSuccess" in label: label = "🔄 Loop In sweep"
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
    
    if not _HOST_SERVICES:
        services = []
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
        "services_managed": not _HOST_SERVICES,
        "local_ip": _local_ip() if _HOST_SERVICES else None,
        "external_ip": _external_ip(),
    }

from fastapi.responses import HTMLResponse as _HTMLResponse


@app.get("/static/sidebar.html")
def sidebar_html():
    return _HTMLResponse(_apply_feature_flags(open("sidebar.html", encoding="utf-8").read()))


app.mount("/static", StaticFiles(directory="."), name="static")
app.mount("/icons", StaticFiles(directory="icons"), name="icons")

@app.get("/dashboard")
def dashboard():
    return _HTMLResponse(_apply_feature_flags(open("index.html", encoding="utf-8").read()))

import hmac as _hmac
import hashlib as _hashlib
import time as _time_auth

_LCC_PASSWORD = os.environ.get("LCC_PASSWORD", "")
_LCC_SESSION_SECRET = os.environ.get("LCC_SESSION_SECRET", "")
_SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
_SESSION_HOURS_ALLOWED = (1, 2, 4, 8, 24, 168, 720)
_session_cfg_cache = {"mtime": None, "hours": 720, "browser_only": False, "valid_after": 0}


def _session_cfg():
    """Session length + sign-out-on-browser-close, read from data.json (cached by mtime)."""
    try:
        mtime = os.path.getmtime(_DATA_JSON_PATH)
        if mtime != _session_cfg_cache["mtime"]:
            data = json.load(open(_DATA_JSON_PATH))
            hours = data.get("session_hours", 720)
            _session_cfg_cache["hours"] = hours if hours in _SESSION_HOURS_ALLOWED else 720
            _session_cfg_cache["browser_only"] = bool(data.get("session_browser_only", False))
            _session_cfg_cache["valid_after"] = int(data.get("sessions_valid_after", 0) or 0)
            _session_cfg_cache["mtime"] = mtime
    except Exception:
        pass
    return _session_cfg_cache


def _session_max_age():
    return int(_session_cfg()["hours"]) * 3600


def _cookie_max_age():
    # None = cookie is deleted when the browser closes
    return None if _session_cfg()["browser_only"] else _session_max_age()

def _make_session_token():
    ts = str(int(_time_auth.time()))
    sig = _hmac.new(_LCC_SESSION_SECRET.encode(), ts.encode(), _hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"

def _verify_session_token(token):
    if not token or not _LCC_SESSION_SECRET:
        return False
    try:
        ts, sig = token.split(".", 1)
        expected = _hmac.new(_LCC_SESSION_SECRET.encode(), ts.encode(), _hashlib.sha256).hexdigest()
        if not _hmac.compare_digest(sig, expected):
            return False
        if int(_time_auth.time()) - int(ts) > _session_max_age():
            return False
        if int(ts) < _session_cfg()["valid_after"]:
            return False
        return True
    except Exception:
        return False

_PW_ITERATIONS = 200_000
_PASSWORD_MANAGED = os.environ.get("LCC_PASSWORD_MANAGED", "") == "1"


def _env_pw_fingerprint():
    return _hashlib.sha256(_LCC_PASSWORD.encode()).hexdigest() if _LCC_PASSWORD else ""


def _hash_password(pw):
    salt = secrets.token_hex(16)
    dk = _hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), _PW_ITERATIONS).hex()
    return f"pbkdf2_sha256${_PW_ITERATIONS}${salt}${dk}"


def _check_password_hash(pw, stored):
    try:
        _, iters, salt, dk = stored.split("$")
        test = _hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(iters)).hex()
        return _hmac.compare_digest(test, dk)
    except Exception:
        return False


def _stored_password_hash():
    if _PASSWORD_MANAGED:
        return None
    try:
        data = json.load(open(_DATA_JSON_PATH))
    except Exception:
        return None
    h = data.get("lcc_password_hash")
    if h and data.get("lcc_password_env_fp") == _env_pw_fingerprint():
        return h
    return None


def _password_ok(pw):
    pw = str(pw or "")
    stored = _stored_password_hash()
    if stored:
        return _check_password_hash(pw, stored)
    return bool(_LCC_PASSWORD) and _hmac.compare_digest(pw.encode(), _LCC_PASSWORD.encode())


_PUBLIC_AUTH_PATHS = {"/api/login", "/login", "/api/nostr/status", "/api/nostr/challenge", "/api/nostr/login"}

@app.middleware("http")
async def auth_gate(request: Request, call_next):
    path = request.url.path
    if path in _PUBLIC_AUTH_PATHS or path.startswith("/icons/"):
        return await call_next(request)
    token = request.cookies.get("lcc_session")
    if _verify_session_token(token):
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return RedirectResponse(url="/login")

@app.get("/login")
def login_page():
    return FileResponse("login.html")

@app.post("/api/login")
def api_login(body: dict = Body(...)):
    password = body.get("password", "")
    if not _password_ok(password):
        raise HTTPException(status_code=401, detail="Invalid password")
    token = _make_session_token()
    resp = JSONResponse({"status": "ok"})
    resp.set_cookie(
        key="lcc_session",
        value=token,
        max_age=_cookie_max_age(),
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return resp

@app.post("/api/logout")
def api_logout():
    resp = JSONResponse({"status": "ok"})
    resp.delete_cookie("lcc_session")
    return resp


# --- Nostr login (NIP-07) ------------------------------------------------------
# A browser extension (Alby, nos2x...) signs a one-time challenge; the nsec never
# leaves the extension. Only npubs listed in Settings may sign in. With no npub
# listed the feature is off and the login page shows no Nostr button.
_NOSTR_AUTH_KIND = 22242
_NOSTR_CHALLENGE_TTL = 120
_nostr_challenges = {}


def _npub_to_hex(npub):
    from nostr_sdk import PublicKey
    try:
        return PublicKey.parse(str(npub).strip()).to_hex()
    except Exception:
        return None


def _nostr_allowed_npubs():
    try:
        return list(json.load(open(_DATA_JSON_PATH)).get("nostr_login_npubs", []))
    except Exception:
        return []


def _nostr_allowed_hex():
    return {h for h in (_npub_to_hex(n) for n in _nostr_allowed_npubs()) if h}


def _nostr_event_id(ev):
    payload = json.dumps(
        [0, ev["pubkey"], ev["created_at"], ev["kind"], ev["tags"], ev["content"]],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return _hashlib.sha256(payload.encode()).hexdigest()


def _nostr_signature_ok(ev):
    from nostr_sdk import Event
    try:
        e = Event.from_json(json.dumps(ev))
        r = e.verify()
        return True if r is None else bool(r)
    except Exception:
        return False


def _session_cookie_response():
    resp = JSONResponse({"status": "ok"})
    resp.set_cookie(
        key="lcc_session",
        value=_make_session_token(),
        max_age=_cookie_max_age(),
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return resp


@app.get("/api/nostr/status")
def nostr_status():
    return {"enabled": bool(_LCC_SESSION_SECRET) and len(_nostr_allowed_hex()) > 0}


@app.get("/api/nostr/challenge")
def nostr_challenge():
    now = int(_time_auth.time())
    for c, exp in list(_nostr_challenges.items()):
        if exp < now:
            _nostr_challenges.pop(c, None)
    if len(_nostr_challenges) > 200:
        _nostr_challenges.clear()
    challenge = secrets.token_hex(32)
    _nostr_challenges[challenge] = now + _NOSTR_CHALLENGE_TTL
    return {"challenge": challenge}


@app.post("/api/nostr/login")
def nostr_login(body: dict = Body(...)):
    fail = HTTPException(status_code=401, detail="Nostr sign-in failed")
    if not _LCC_SESSION_SECRET:
        raise fail
    ev = body.get("event")
    if not isinstance(ev, dict):
        raise fail
    try:
        tags = ev["tags"]
        challenge = next(t[1] for t in tags if isinstance(t, list) and len(t) > 1 and t[0] == "challenge")
        exp = _nostr_challenges.pop(challenge, None)
        now = int(_time_auth.time())
        if exp is None or exp < now:
            raise HTTPException(status_code=401, detail="Sign-in request expired, please try again")
        if ev["kind"] != _NOSTR_AUTH_KIND or abs(now - int(ev["created_at"])) > _NOSTR_CHALLENGE_TTL:
            raise fail
        if ev["pubkey"] not in _nostr_allowed_hex():
            raise HTTPException(status_code=403, detail="This Nostr key is not allowed to sign in")
        if ev.get("id") != _nostr_event_id(ev) or not _nostr_signature_ok(ev):
            raise fail
    except HTTPException:
        raise
    except Exception:
        raise fail
    return _session_cookie_response()


@app.get("/api/settings/nostr-login")
def get_nostr_login_settings():
    return {"npubs": _nostr_allowed_npubs()}


@app.post("/api/settings/nostr-login")
def set_nostr_login_settings(body: dict = Body(...)):
    npubs = [str(n).strip() for n in body.get("npubs", []) if str(n).strip()]
    for n in npubs:
        if n.startswith("nsec"):
            raise HTTPException(status_code=400, detail="That is a secret key (nsec). Never paste it anywhere. Use your npub instead.")
        if not n.startswith("npub1") or not _npub_to_hex(n):
            raise HTTPException(status_code=400, detail=f"Not a valid npub: {n[:16]}...")
    data = json.load(open(_DATA_JSON_PATH))
    data["nostr_login_npubs"] = npubs
    with open(_DATA_JSON_PATH, "w") as f:
        json.dump(data, f, indent=2)
    return {"npubs": npubs}


@app.get("/api/settings/session")
def get_session_settings():
    cfg = _session_cfg()
    return {"hours": cfg["hours"], "browser_only": cfg["browser_only"]}


@app.post("/api/settings/session")
def set_session_settings(body: dict = Body(...)):
    try:
        hours = int(body.get("hours", 720))
    except Exception:
        hours = 0
    if hours not in _SESSION_HOURS_ALLOWED:
        raise HTTPException(status_code=400, detail="Invalid session duration")
    data = json.load(open(_DATA_JSON_PATH))
    data["session_hours"] = hours
    data["session_browser_only"] = bool(body.get("browser_only", False))
    with open(_DATA_JSON_PATH, "w") as f:
        json.dump(data, f, indent=2)
    return {"hours": hours, "browser_only": data["session_browser_only"]}


@app.get("/api/settings/password")
def get_password_settings():
    return {"managed": _PASSWORD_MANAGED}


@app.post("/api/settings/password")
def change_password(body: dict = Body(...)):
    if _PASSWORD_MANAGED:
        raise HTTPException(status_code=403, detail="The password is managed by your node's operating system. On StartOS, use Actions → Set Login Password.")
    current = str(body.get("current", ""))
    new = str(body.get("new", ""))
    if not _password_ok(current):
        raise HTTPException(status_code=401, detail="Current password is wrong")
    if len(new) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    data = json.load(open(_DATA_JSON_PATH))
    data["lcc_password_hash"] = _hash_password(new)
    data["lcc_password_env_fp"] = _env_pw_fingerprint()
    data["sessions_valid_after"] = int(_time_auth.time())
    data.pop("lcc_password", None)
    data.pop("first_boot_password", None)
    with open(_DATA_JSON_PATH, "w") as f:
        json.dump(data, f, indent=2)
    return _session_cookie_response()

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
        except Exception as e:
            print(f"[strategy] getchaninfo failed: {e}")  # Already connected is fine
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
            if result.get("status") == "SUCCEEDED":
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



_STRAT_FULL_PCT = 95        # "full" for the recycle check
_STRAT_LOW_FEE = 50         # ppm: fee already low enough that price is not the problem
_STRAT_WATCH_DAYS = 7       # days full at a low fee with no traffic before suggesting a close
_STRAT_CLOSE_VBYTES = 200   # rough size of a cooperative close
_STRAT_LOOPOUT_RATE = 0.0035  # ~0.35% real Loop Out cost seen in practice (fees + routing)
_strat_fee_cache = {"t": 0, "rate": 2}


def _strategy_fee_rate():
    """sat/vB for a close that confirms within an hour or so (cached 10 min)."""
    now = time.time()
    if now - _strat_fee_cache["t"] < 600:
        return _strat_fee_cache["rate"]
    rate = _strat_fee_cache["rate"]
    try:
        r = requests.get("https://mempool.space/api/v1/fees/recommended", timeout=5).json()
        rate = max(1, int(r.get("hourFee") or r.get("halfHourFee") or 2))
    except Exception:
        pass
    _strat_fee_cache.update(t=now, rate=rate)
    return rate


@app.get("/api/strategy")
def get_strategy():
    channels = run_lncli("listchannels")
    try:
        my_pubkey = run_lncli("getinfo").get("identity_pubkey", "")
    except Exception:
        my_pubkey = ""

    # Traffic per channel over the last 7 days
    out_7d, in_7d = {}, {}
    try:
        start_7d = int(time.time()) - 7 * 86400
        fwd = run_lncli("fwdinghistory", f"--start_time={start_7d}", "--max_events=50000")
        for ev in fwd.get("forwarding_events", []):
            co, ci = str(ev.get("chan_id_out", "")), str(ev.get("chan_id_in", ""))
            out_7d[co] = out_7d.get(co, 0) + int(ev.get("amt_out", 0) or 0)
            in_7d[ci] = in_7d.get(ci, 0) + int(ev.get("amt_in", 0) or 0)
    except Exception as e:
        print(f"[strategy] fwdinghistory failed: {e}")

    try:
        data = json.load(open(_DATA_JSON_PATH))
    except Exception:
        data = {}
    watch = dict(data.get("strategy_watch", {}))
    watch_changed = False
    now = int(time.time())
    fee_rate = _strategy_fee_rate()

    results = []
    seen = set()
    for ch in channels.get("channels", []):
        cap = int(ch.get("capacity", 0))
        local = int(ch.get("local_balance", 0))
        local_pct = round(local / cap * 100) if cap > 0 else 0
        alias = ch.get("peer_alias", "Unknown")
        cp = ch.get("channel_point", "")
        scid = str(ch.get("scid") or ch.get("chan_id", ""))
        seen.add(cp)
        my_fee = 0
        peer_fee = 0
        try:
            info = run_lncli("getchaninfo", f"--chan_id={scid}")
            if info.get("node1_pub") == my_pubkey:
                my_fee = int(info.get("node1_policy", {}).get("fee_rate_milli_msat", 0))
                peer_fee = int(info.get("node2_policy", {}).get("fee_rate_milli_msat", 0))
            else:
                my_fee = int(info.get("node2_policy", {}).get("fee_rate_milli_msat", 0))
                peer_fee = int(info.get("node1_policy", {}).get("fee_rate_milli_msat", 0))
        except Exception as e:
            print(f"[strategy] getchaninfo failed: {e}")
        initiator = ch.get("initiator", False)
        sats_out = out_7d.get(scid, 0)
        sats_in = in_7d.get(scid, 0)

        # How long has this channel been full at a low fee with nothing going out?
        stuck = local_pct >= _STRAT_FULL_PCT and my_fee <= _STRAT_LOW_FEE and sats_out == 0
        if stuck:
            if cp not in watch:
                watch[cp] = now
                watch_changed = True
            stuck_days = (now - int(watch[cp])) / 86400
        else:
            if cp in watch:
                watch.pop(cp)
                watch_changed = True
            stuck_days = 0

        recycle = None
        if stuck:
            close_cost = _STRAT_CLOSE_VBYTES * fee_rate
            recycle = {
                "local": local,
                "close_cost": close_cost,
                "close_paid_by": "you" if initiator else "peer",
                "loopout_cost": int(local * _STRAT_LOOPOUT_RATE),
            }

        if stuck and stuck_days >= _STRAT_WATCH_DAYS:
            assessment = (f"Full at {my_fee} ppm for {int(stuck_days)} days, nothing routed out. "
                          f"Recycle {local:,} sats: closing costs about {recycle['close_cost']:,} sats"
                          f"{' (paid by peer)' if not initiator else ''}, a Loop Out about {recycle['loopout_cost']:,}.")
            action = "Recycle: cooperative close"
            color = "red"
        elif stuck:
            assessment = f"Full at a low fee, nothing routed out in 7 days. Watching: day {int(stuck_days) + 1} of {_STRAT_WATCH_DAYS}."
            action = "Wait, then recycle if still stuck"
            color = "orange"
        elif local_pct >= 90 and my_fee > _STRAT_LOW_FEE:
            assessment = "Full, fee still high: lower it first so traffic can leave"
            action = (f"Drain {peer_fee + 10}-{peer_fee + 25} ppm" if peer_fee < 100
                      else f"{max(25, peer_fee // 4)}-{max(50, peer_fee // 2)} ppm")
            color = "green"
        elif not initiator and local_pct < 90:
            assessment = "Inbound lifeline (peer opened)"
            action = "Keep as-is"
            color = "blue"
        elif peer_fee > 500 and sats_out == 0 and sats_in == 0:
            assessment = "Peer fee too high and no traffic in 7 days"
            action = "CLOSE / Loop Out"
            color = "red"
        elif peer_fee > 300:
            assessment = "High peer fee" + (" (but routing, keep)" if (sats_out or sats_in) else "")
            action = "Monitor"
            color = "orange"
        elif local_pct < 20:
            assessment = "Nearly empty" + (": selling well, refill if it pays" if sats_out else "")
            action = "Monitor / refill (Loop In)" if sats_out else "Monitor"
            color = "orange"
        else:
            assessment = "Balanced"
            action = f"Monitor / {max(25, peer_fee // 4)} ppm"
            color = "orange"
        results.append({
            "alias": alias,
            "capacity": cap,
            "local_pct": local_pct,
            "my_fee": my_fee,
            "peer_fee": peer_fee,
            "initiator": initiator,
            "out_7d": sats_out,
            "in_7d": sats_in,
            "stuck_days": round(stuck_days, 1),
            "recycle": recycle,
            "assessment": assessment,
            "action": action,
            "color": color,
            "channel_point": cp,
            "remote_pubkey": ch.get("remote_pubkey", ""),
        })

    for cp in list(watch):
        if cp not in seen:
            watch.pop(cp)
            watch_changed = True
    if watch_changed:
        try:
            data = json.load(open(_DATA_JSON_PATH))
            data["strategy_watch"] = watch
            with open(_DATA_JSON_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[strategy] could not save watch list: {e}")

    results.sort(key=lambda x: {"red": 0, "green": 1, "orange": 2, "blue": 3}.get(x["color"], 4))
    return {"channels": results, "fee_rate": fee_rate, "watch_days": _STRAT_WATCH_DAYS}


@app.get("/api/inbound-health")
def inbound_health():
    """How easily this node can be paid: room each peer has to send to us, what they charge, who sends."""
    channels = run_lncli("listchannels").get("channels", [])
    try:
        my_pubkey = run_lncli("getinfo").get("identity_pubkey", "")
    except Exception:
        my_pubkey = ""
    in_7d = {}
    try:
        start_7d = int(time.time()) - 7 * 86400
        fwd = run_lncli("fwdinghistory", f"--start_time={start_7d}", "--max_events=50000")
        for ev in fwd.get("forwarding_events", []):
            ci = str(ev.get("chan_id_in", ""))
            in_7d[ci] = in_7d.get(ci, 0) + int(ev.get("amt_in", 0) or 0)
    except Exception as e:
        print(f"[inbound] fwdinghistory failed: {e}")

    rows, by_peer = [], {}
    total_cap = total_room = cheap_room = 0
    for ch in channels:
        if not ch.get("active", True):
            continue
        cap = int(ch.get("capacity", 0) or 0)
        room = int(ch.get("remote_balance", 0) or 0)
        scid = str(ch.get("scid") or ch.get("chan_id", ""))
        pk = ch.get("remote_pubkey", "")
        peer_ppm, peer_base = None, None
        try:
            info = run_lncli("getchaninfo", f"--chan_id={scid}")
            pol = info.get("node2_policy", {}) if info.get("node1_pub") == my_pubkey else info.get("node1_policy", {})
            peer_ppm = int(pol.get("fee_rate_milli_msat", 0) or 0)
            peer_base = int(pol.get("fee_base_msat", 0) or 0)
        except Exception:
            pass
        sent = in_7d.get(scid, 0)
        total_cap += cap
        total_room += room
        if peer_ppm is not None and peer_ppm <= 200:
            cheap_room += room
        p = by_peer.setdefault(pk, {"alias": ch.get("peer_alias", pk[:12]), "room": 0})
        p["room"] += room
        rows.append({
            "alias": ch.get("peer_alias", pk[:12]),
            "capacity": cap,
            "room": room,
            "room_pct": round(room / cap * 100) if cap else 0,
            "peer_ppm": peer_ppm,
            "peer_base_msat": peer_base,
            "sent_7d": sent,
        })

    senders = sorted([r for r in rows if r["sent_7d"] > 0], key=lambda r: -r["sent_7d"])
    low_senders = [r for r in senders if r["room_pct"] < 10]
    top_peer = max(by_peer.values(), key=lambda p: p["room"]) if by_peer else None
    top_share = round(top_peer["room"] / total_room * 100) if (top_peer and total_room) else 0

    if senders and len(low_senders) >= max(1, (len(senders) + 1) // 2) or top_share >= 60:
        status, label = "red", "Hard to reach"
    elif low_senders or top_share >= 40:
        status, label = "yellow", "Tight"
    else:
        status, label = "green", "Easy to reach"

    hints = []
    if low_senders:
        names = ", ".join(r["alias"] for r in low_senders[:3])
        hints.append(f"Busy senders nearly full ({names}): give them a low fee (Drain & Trap) so traffic leaves through them and frees room.")
    if top_share >= 40 and top_peer:
        hints.append(f"{top_share}% of your room to receive sits with {top_peer['alias']}. Inbound from more peers (channels opened to you) makes you easier to pay.")
    if not hints:
        hints.append("Room to receive is spread well across your senders.")

    rows.sort(key=lambda r: (-r["sent_7d"], -r["room"]))
    return {
        "status": status,
        "label": label,
        "total_room": total_room,
        "total_capacity": total_cap,
        "room_pct": round(total_room / total_cap * 100) if total_cap else 0,
        "cheap_room": cheap_room,
        "top_peer": top_peer["alias"] if top_peer else "",
        "top_share": top_share,
        "senders": len(senders),
        "low_senders": len(low_senders),
        "hints": hints,
        "channels": rows,
    }


@app.post("/api/rebalance-targeted")
def rebalance_targeted(body: dict = Body(...)):
    if MOCK:
        return {"status": "mock"}
    out_pubkey = body.get("out_pubkey", "")
    in_pubkey = body.get("in_pubkey", "")
    amount = int(body.get("amount", 50000))
    max_fee = int(body.get("max_fee", 100))
    if not out_pubkey or not in_pubkey:
        raise HTTPException(status_code=400, detail="Both out_pubkey and in_pubkey required")
    try:
        channels = run_lncli("listchannels")["channels"]
        out_ch = [c for c in channels if c["remote_pubkey"] == out_pubkey]
        in_ch = [c for c in channels if c["remote_pubkey"] == in_pubkey]
        if not out_ch or not in_ch:
            return {"status": "error", "detail": "Channel not found"}
        out_chan_id = str(out_ch[0].get("scid", out_ch[0].get("chan_id", "")))
        invoice = run_lncli("addinvoice", "--amt=" + str(amount), "--memo=Rebalance: " + out_ch[0].get("peer_alias", "?")[:20] + " -> " + in_ch[0].get("peer_alias", "?")[:20])
        payment_request = invoice.get("payment_request")
        pay_args = [
            "sendpayment",
            "--pay_req=" + payment_request,
            "--outgoing_chan_id=" + out_chan_id,
            "--last_hop=" + in_pubkey,
            "--allow_self_payment",
            "--force",
            "--fee_limit=" + str(max_fee),
            "--timeout=90s",
            "--json"
        ]
        result = run_lncli(*pay_args)
        fee = int(result.get("fee_sat", 0)) if result.get("fee_sat") else 0
        if result.get("status") == "SUCCEEDED":
            return {"status": "success", "detail": "Moved " + str(amount) + " sats", "fee": fee,
                    "from": out_ch[0].get("peer_alias", out_pubkey[:16]),
                    "to": in_ch[0].get("peer_alias", in_pubkey[:16])}
        else:
            reason = result.get("failure_reason", "UNKNOWN")
            friendly = {
                "FAILURE_REASON_NO_ROUTE": f"No profitable route right now: nothing reaches this channel for {max_fee} sats or less ({round(max_fee * 1_000_000 / max(amount, 1)):,} ppm). Nothing was paid. Raising the max fee above what this channel earns would lose money; for busy sinks like LNBiG a Loop In is usually far cheaper.",
                "FAILURE_REASON_TIMEOUT": "Payment timed out. Peer may be offline — try again later or try different channels",
                "FAILURE_REASON_INSUFFICIENT_BALANCE": "Not enough sats in the outbound channel. Try a smaller amount",
                "FAILURE_REASON_INCORRECT_PAYMENT_DETAILS": "Invoice expired — try again",
                "FAILURE_REASON_ERROR": "Payment error — check channel status",
                "FAILURE_REASON_FEE_INSUFFICIENT": "Routing fee exceeds your max limit (" + str(max_fee) + " sats). Increase max fee and try again",
                "UNKNOWN": "Unknown error — check lncli logs",
            }.get(reason, reason)
            return {"status": "failed", "detail": friendly, "raw_reason": reason}
    except HTTPException as he:
        err = he.detail if hasattr(he, 'detail') else str(he)
        if "FAILED" in err:
            friendly = "Rebalance failed. Try: increase max fee, reduce amount, or pick different channels"
        elif "insufficient" in err.lower():
            friendly = "Not enough sats in this channel"
        elif "timeout" in err.lower():
            friendly = "Payment timed out — peer may be offline"
        else:
            friendly = err
        return {"status": "error", "detail": friendly}
    except Exception as e:
        err = str(e)
        if "insufficient" in err.lower():
            friendly = "Not enough sats in this channel"
        elif "timeout" in err.lower():
            friendly = "Payment timed out — peer may be offline"
        else:
            friendly = err
        return {"status": "error", "detail": friendly}

@app.get("/api/accounting")
def get_accounting(days: int = 365):
    import time, csv, io
    start_s = int(time.time()) - (days * 86400) if days < 9999 else 1231006505
    rows = []
    try:
        fwd = run_lncli("fwdinghistory", f"--start_time={start_s}", "--max_events=50000")
        for e in fwd.get("forwarding_events", []):
            ts = int(e.get("timestamp", 0))
            rows.append({"date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)), "type": "routing_income", "amount_sats": int(e.get("fee_msat", 0)) // 1000, "fee_sats": 0, "description": f"{e.get('peer_alias_in', e.get('chan_id_in',''))} -> {e.get('peer_alias_out', e.get('chan_id_out',''))} ({e.get('amt_in', 0)} sats)", "txid": e.get("timestamp_ns", "")})
    except Exception as ex:
        print(f"[ACCT] fwd error: {ex}")
    try:
        payments = run_lncli("listpayments", "--max_payments=1000")
        # Build pubkey to alias map
        alias_map = {ch.get("remote_pubkey",""): ch.get("peer_alias","") for ch in run_lncli("listchannels").get("channels", [])}
        for p in payments.get("payments", []):
            ts = int(p.get("creation_date", 0))
            if ts < start_s: continue
            fee = int(p.get("fee_sat", 0))
            amt = int(p.get("value_sat", 0))
            rows.append({"date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)), "type": "payment_sent", "amount_sats": -amt, "fee_sats": -fee, "description": "Lightning payment", "txid": p.get("payment_hash", "")[:16]})
    except Exception as ex:
        print(f"[ACCT] pay error: {ex}")
    try:
        txns = run_lncli("listchaintxns")
        for t in txns.get("transactions", []):
            ts = int(t.get("time_stamp", 0))
            if ts < start_s: continue
            amt = int(t.get("amount", 0))
            fee = int(t.get("total_fees", 0))
            tx_type = "channel_open" if amt < 0 else "channel_close" if amt > 0 else "onchain"
            rows.append({"date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)), "type": tx_type, "amount_sats": amt, "fee_sats": -fee, "description": t.get("label", tx_type), "txid": t.get("tx_hash", "")[:16]})
    except Exception as ex:
        print(f"[ACCT] chain error: {ex}")
    try:
        data = json.load(open(_DATA_JSON_PATH))
        rate_cents = float(data.get("energy_rate", 0))
        watts = float(data.get("energy_watts", 0))
        btc_price = float(data.get("energy_btc_price", 0))
        if rate_cents and watts and btc_price:
            energy_usd = (watts / 1000) * 24 * min(days, 365) * (rate_cents / 100)
            energy_sats = int(energy_usd / btc_price * 100000000)
        else:
            energy_usd = 0
            energy_sats = 0
    except:
        energy_usd = 0
        energy_sats = 0
    if energy_sats > 0:
        rows.append({"date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())), "type": "energy_cost", "amount_sats": -energy_sats, "fee_sats": 0, "description": f"Electricity ({days}d)", "txid": ""})
    rows.sort(key=lambda r: r["date"])
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["date", "type", "amount_sats", "fee_sats", "description", "txid"])
    writer.writeheader()
    writer.writerows(rows)
    routing_income = sum(r["amount_sats"] for r in rows if r["type"] == "routing_income")
    total_fees = sum(r["fee_sats"] for r in rows)
    return {"csv": output.getvalue(), "summary": {"routing_income": routing_income, "total_fees_paid": total_fees, "energy_cost_sats": -energy_sats, "energy_cost_usd": round(energy_usd, 2), "net": routing_income + total_fees - energy_sats, "total_events": len(rows)}}

@app.get("/api/estimatefee")
def estimate_rebalance_fee(target_pubkey: str = "", amount: int = 0):
    if not target_pubkey:
        raise HTTPException(status_code=400, detail="target_pubkey required")
    if amount <= 0:
        data = json.load(open(_DATA_JSON_PATH))
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
def update_fees(base_fee_msat: int = 1000, fee_rate_ppm: int = 100, time_lock_delta: int = 40, chan_point: str = None, peer_pubkey: str = None):
    if MOCK:
        return {"status": "mock"}
    try:
        fee_rate = fee_rate_ppm / 1_000_000
        base_args = [
            "updatechanpolicy",
            f"--base_fee_msat={base_fee_msat}",
            f"--fee_rate={fee_rate}",
            f"--time_lock_delta={time_lock_delta}"
        ]
        if peer_pubkey:
            points = [c.get("channel_point", "") for c in run_lncli("listchannels").get("channels", [])
                      if c.get("remote_pubkey") == peer_pubkey]
            if not points:
                raise HTTPException(status_code=404, detail="No channels with that peer")
            failed = 0
            for cp in points:
                result = run_lncli(*base_args, f"--chan_point={cp}")
                failed += len(result.get("failed_updates", []))
            return {"status": "done", "updated": len(points) - failed, "failed": failed,
                    "message": f"Updated {len(points) - failed} of {len(points)} channels with this peer"}
        args = list(base_args)
        if chan_point:
            args.append(f"--chan_point={chan_point}")
        result = run_lncli(*args)
        failed = result.get("failed_updates", [])
        return {"status": "done", "failed": len(failed), "message": f"Updated all channels — {len(failed)} failed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

_REBAL_COST_SHARE = 0.5   # pay at most half of what the receiving channel earns per sat
_REBAL_MAX_ATTEMPTS = 10  # per "Rebalance All" press


def _rebal_my_fee(ch, my_pubkey):
    """(our fee ppm on this channel, numeric channel id)."""
    try:
        info = run_lncli("getchaninfo", f"--chan_point={ch.get('channel_point', '')}")
        pol = info.get("node1_policy", {}) if info.get("node1_pub") == my_pubkey else info.get("node2_policy", {})
        return int(pol.get("fee_rate_milli_msat", 0) or 0), info.get("channel_id")
    except Exception:
        return 0, None


@app.post("/api/rebalance")
def rebalance_channels(target_pubkey: str = None):
    if MOCK:
        return {"status": "mock", "message": "Rebalance simulated"}
    try:
        channels = run_lncli("listchannels")["channels"]
        pct = lambda c: int(c["local_balance"]) / int(c["capacity"]) if int(c["capacity"]) > 0 else 0
        overfull = [c for c in channels if int(c["capacity"]) > 0 and pct(c) > 0.80]
        underfull = [c for c in channels if int(c["capacity"]) > 0 and pct(c) < 0.20]

        if target_pubkey:
            target = [c for c in channels if c["remote_pubkey"] == target_pubkey]
            if target:
                if pct(target[0]) > 0.50:
                    overfull = [target[0]]
                else:
                    underfull = [target[0]]

        if not overfull or not underfull:
            return {"status": "balanced", "message": "No rebalancing needed", "results": [],
                    "summary": {"moved": 0, "sats_moved": 0, "fees": 0, "no_route": 0, "skipped": 0}}

        try:
            my_pubkey = run_lncli("getinfo").get("identity_pubkey", "")
        except Exception:
            my_pubkey = ""
        settings = json.load(open(_DATA_JSON_PATH))
        max_amount = int(settings.get("rebalance_amount", 50000))

        src_info = {c.get("channel_point"): _rebal_my_fee(c, my_pubkey) for c in overfull}
        dst_info = {c.get("channel_point"): _rebal_my_fee(c, my_pubkey) for c in underfull}
        overfull.sort(key=lambda c: -pct(c))                                  # fullest sources first
        underfull.sort(key=lambda c: -dst_info[c.get("channel_point")][0])   # best-earning exits first

        results, attempts = [], 0
        for dst in underfull:
            dst_ppm = dst_info[dst.get("channel_point")][0]
            dst_alias = dst.get("peer_alias", dst["remote_pubkey"][:16])
            moved = False
            for src in overfull:
                if moved:
                    break
                src_alias = src.get("peer_alias", src["remote_pubkey"][:16])
                amount = min(int(src["local_balance"]) - int(int(src["capacity"]) * 0.50),
                             int(int(dst["capacity"]) * 0.50) - int(dst["local_balance"]),
                             max_amount)
                if amount < 1000:
                    continue
                fee_cap = int(amount * dst_ppm * _REBAL_COST_SHARE / 1_000_000)
                if fee_cap < 1:
                    results.append({"from": "any", "to": dst_alias, "amount": amount, "status": "skipped",
                                    "reason": f"{dst_alias} charges {dst_ppm} ppm, too little to pay for a rebalance"})
                    break
                if attempts >= _REBAL_MAX_ATTEMPTS:
                    results.append({"from": src_alias, "to": dst_alias, "amount": amount, "status": "skipped",
                                    "reason": "attempt limit reached for this run"})
                    continue
                attempts += 1
                try:
                    invoice = run_lncli("addinvoice", f"--amt={amount}", "--memo=LCC Rebalance: " + src_alias[:20] + " -> " + dst_alias[:20])
                    pay_args = [
                        "sendpayment",
                        "--pay_req=" + invoice.get("payment_request"),
                        "--last_hop=" + dst["remote_pubkey"],
                        "--allow_self_payment",
                        "--force",
                        f"--fee_limit={fee_cap}",
                        "--timeout=30s",
                        "--json",
                    ]
                    src_id = src_info[src.get("channel_point")][1]
                    if src_id:
                        pay_args.append(f"--outgoing_chan_id={src_id}")
                    result = run_lncli(*pay_args)
                    if result.get("status") == "SUCCEEDED":
                        fee = int(result.get("fee_sat", 0) or 0)
                        results.append({"from": src_alias, "to": dst_alias, "amount": amount, "fee": fee,
                                        "fee_cap": fee_cap, "status": "success"})
                        _log_journal(f"Rebalance: {src_alias} \u2192 {dst_alias}",
                                     f"Moved {amount:,} sats | Fee: {fee} sats (cap {fee_cap}, {dst_alias} earns {dst_ppm} ppm)",
                                     "auto-rebalance")
                        moved = True
                    else:
                        results.append({"from": src_alias, "to": dst_alias, "amount": amount, "fee_cap": fee_cap,
                                        "status": "no_route", "reason": result.get("failure_reason", "FAILED")})
                except Exception as ex:
                    results.append({"from": src_alias, "to": dst_alias, "amount": amount,
                                    "status": "no_route", "reason": str(ex)[:200]})

        ok = [r for r in results if r["status"] == "success"]
        summary = {
            "moved": len(ok),
            "sats_moved": sum(r["amount"] for r in ok),
            "fees": sum(r.get("fee", 0) for r in ok),
            "no_route": len([r for r in results if r["status"] == "no_route"]),
            "skipped": len([r for r in results if r["status"] == "skipped"]),
        }
        return {"status": "done", "results": results, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/rebalance")
def set_rebalance_schedule(hours: int = 24, amount: int = 50000):
    data = json.load(open(_DATA_JSON_PATH))
    data["auto_rebalance_hours"] = hours
    data["rebalance_amount"] = amount
    with open(_DATA_JSON_PATH, "w") as f:
        json.dump(data, f, indent=2)
    return {"auto_rebalance_hours": hours, "rebalance_amount": amount, "status": "updated"}


@app.get("/api/settings/reconnect")
def get_reconnect_setting():
    return {"enabled": _auto_reconnect_enabled()}


@app.post("/api/settings/reconnect")
def set_reconnect_setting(body: dict = Body(...)):
    try:
        data = json.load(open(_DATA_JSON_PATH))
    except Exception:
        data = {}
    data["auto_reconnect_enabled"] = bool(body.get("enabled", False))
    with open(_DATA_JSON_PATH, "w") as f:
        json.dump(data, f, indent=2)
    return {"enabled": data["auto_reconnect_enabled"], "status": "updated"}

@app.get("/api/journal")
def get_journal():
    import os
    journal_path = os.path.join(LCC_DATA_DIR, "journal.json")
    try:
        with open(journal_path, "r") as f:
            return {"entries": json.load(f)}
    except:
        return {"entries": []}

@app.post("/api/journal")
def save_journal(request: Request):
    import asyncio, os, time
    journal_path = os.path.join(LCC_DATA_DIR, "journal.json")
    try:
        body = asyncio.run(request.json())
        # Load existing entries
        try:
            with open(journal_path, "r") as f:
                existing = json.load(f)
        except:
            existing = []
        # If sending full entries array — bulk save
        if "entries" in body:
            entries = body["entries"]
            with open(journal_path, "w") as f:
                json.dump(entries, f, indent=2)
            return {"status": "saved", "count": len(entries)}
        # If sending single entry — append to existing
        elif "title" in body:
            new_entry = {
                "id": int(time.time() * 1000),
                "title": body.get("title", ""),
                "body": body.get("body", ""),
                "tag": body.get("tag", "note"),
                "block": body.get("block", 0),
                "date": body.get("date", int(time.time() * 1000))
            }
            existing.insert(0, new_entry)
            with open(journal_path, "w") as f:
                json.dump(existing, f, indent=2)
            return {"status": "saved", "count": len(existing), "entry": new_entry}
        else:
            return {"status": "error", "detail": "No entries or title provided"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/lnbits")
def get_lnbits_settings():
    data = json.load(open(_DATA_JSON_PATH))
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

@app.get("/api/version")
def get_version():
    return {"version": LCC_VERSION}


@app.get("/api/tier")
def get_tier():
    data = json.load(open(_DATA_JSON_PATH))
    return {"tier": data.get("tier", "community")}

@app.post("/api/tier/{key}")
def set_tier(key: str):
    KEYS = {}
    env_keys = os.getenv("LCC_LICENSE_KEYS", "")
    for pair in env_keys.split(","):
        if ":" in pair:
            k, v = pair.strip().split(":", 1)
            KEYS[k.strip()] = v.strip()
    if not KEYS:
        KEYS = {"DEMO": "community"}
    if key not in KEYS:
        raise HTTPException(status_code=403, detail="Invalid license key")
    data = json.load(open(_DATA_JSON_PATH))
    data["tier"] = KEYS[key]
    with open(_DATA_JSON_PATH, "w") as f:
        json.dump(data, f, indent=2)
    return {"tier": data["tier"], "status": "activated"}


# ─── NWC (Nostr Wallet Connect) ───────────────────────────────────────────────
import secrets
from nostr_sdk import Keys

NWC_RELAY = "wss://relay.primal.net"
NWC_DATA_FILE = os.path.join(LCC_DATA_DIR, "nwc_connections.json")

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
        cfg = json.load(open(_DATA_JSON_PATH))
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



# ─── Drain & Trap Channel Strategy ───────────────────────────────────────────
@app.get("/api/channel-strategies")
def get_channel_strategies():
    data = json.load(open(_DATA_JSON_PATH))
    return {"strategies": data.get("channel_strategies", {})}

@app.post("/api/channel-strategies/{chan_point:path}")
def set_channel_strategy(chan_point: str, body: dict = Body(...)):
    f = _DATA_JSON_PATH
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

def _log_journal(title, body, tag="auto-rebalance"):
    """Write an entry to the node journal"""
    import time as _t
    journal_path = os.path.join(LCC_DATA_DIR, "journal.json")
    try:
        with open(journal_path, "r") as f:
            entries = json.load(f)
    except:
        entries = []
    entries.insert(0, {
        "id": int(_t.time() * 1000),
        "title": title,
        "body": body,
        "tag": tag,
        "block": 0,
        "date": int(_t.time() * 1000)
    })
    with open(journal_path, "w") as f:
        json.dump(entries, f, indent=2)

def auto_rebalance_job():
    import time as _time
    while True:
        try:
            data = json.load(open(_DATA_JSON_PATH))
            per_channel = data.get("channel_auto_rebalance", {})
            now = int(_time.time())
            
            if per_channel and not MOCK:
                channels = run_lncli("listchannels")["channels"]
                underfull = [c for c in channels if int(c["capacity"]) > 0 and
                             int(c["local_balance"]) / int(c["capacity"]) < 0.20]
                
                for ch in channels:
                    cp = ch.get("channel_point", "")
                    settings = per_channel.get(cp)
                    if not settings or not settings.get("enabled"):
                        continue
                    
                    # Check if it's time to run
                    mode = settings.get("mode", "interval")
                    last_run = settings.get("last_run", 0)
                    
                    if mode == "scheduled":
                        import datetime as _dt
                        current_hour = _dt.datetime.now().hour
                        scheduled = settings.get("scheduled_hours", [])
                        if current_hour not in scheduled:
                            continue
                        # Only run once per scheduled hour
                        if now - last_run < 3500:
                            continue
                    else:
                        interval = settings.get("hours", 24) * 3600
                        if now - last_run < interval:
                            continue
                    
                    # Check if channel needs rebalancing
                    cap = int(ch.get("capacity", 1))
                    local = int(ch.get("local_balance", 0))
                    pct = (local / cap) * 100
                    target = settings.get("target_pct", 50)
                    
                    if pct <= target + 10:
                        continue  # Already near target
                    
                    # Find best underfull destination
                    if not underfull:
                        continue
                    
                    amount = settings.get("amount", 10000)
                    max_fee = settings.get("max_fee", 400)
                    alias = settings.get("alias", cp[:16])
                    
                    try:
                        # Get channel ID
                        src_chan_id = None
                        chan_info = run_lncli("getchaninfo", f"--chan_point={cp}")
                        src_chan_id = chan_info.get("channel_id")
                        
                        dst = underfull[0]
                        _dst_ppm, _ = _rebal_my_fee(dst, run_lncli("getinfo").get("identity_pubkey", ""))
                        _fee_cap = max(1, min(int(max_fee), int(amount * _dst_ppm * _REBAL_COST_SHARE / 1_000_000)))
                        invoice = run_lncli("addinvoice", f"--amt={amount}", f"--memo=Auto-Rebalance: {alias}")
                        payment_request = invoice.get("payment_request")
                        
                        pay_args = [
                            "sendpayment",
                            "--pay_req=" + payment_request,
                            "--last_hop=" + dst["remote_pubkey"],
                            "--allow_self_payment",
                            "--force",
                            "--fee_limit=" + str(_fee_cap),
                            "--timeout=30s",
                            "--json"
                        ]
                        if src_chan_id:
                            pay_args.append(f"--outgoing_chan_id={src_chan_id}")
                        
                        result = run_lncli(*pay_args)
                        fee = int(result.get("fee_sat", 0)) if result.get("fee_sat") else 0
                        dst_alias = dst.get('peer_alias', '?')
                        if result.get("status") == "SUCCEEDED":
                            print(f"[AUTO-REBAL] {alias} -> {dst_alias}: SUCCESS ({amount} sats, fee: {fee})")
                            _log_journal(
                                f"Auto-rebalance: {alias} → {dst_alias}",
                                f"Moved {amount:,} sats | Fee: {fee} sats | Route: {alias} → {dst_alias}",
                                "auto-rebalance"
                            )
                            # Reset fail counter and save ROI tracking entry
                            import time as _t2
                            data = json.load(open(_DATA_JSON_PATH))
                            if cp in data.get("channel_auto_rebalance", {}):
                                data["channel_auto_rebalance"][cp]["consecutive_fails"] = 0
                            
                            # ROI tracker — save rebalance event for 2hr and 24hr comparison
                            if "rebalance_roi" not in data:
                                data["rebalance_roi"] = []
                            data["rebalance_roi"].append({
                                "channel": alias,
                                "chan_point": cp,
                                "time": int(_t2.time()),
                                "amount": amount,
                                "fee_paid": fee,
                                "routing_2hr": None,
                                "routing_24hr": None
                            })
                            # Keep last 100 entries
                            data["rebalance_roi"] = data["rebalance_roi"][-100:]
                            
                            with open(_DATA_JSON_PATH, "w") as f:
                                json.dump(data, f, indent=2)
                        else:
                            reason = result.get("failure_reason", "unknown")
                            print(f"[AUTO-REBAL] {alias} -> {dst_alias}: FAILED ({reason})")
                            # Track consecutive failures
                            data = json.load(open(_DATA_JSON_PATH))
                            if cp in data.get("channel_auto_rebalance", {}):
                                fails = data["channel_auto_rebalance"][cp].get("consecutive_fails", 0) + 1
                                data["channel_auto_rebalance"][cp]["consecutive_fails"] = fails
                                if fails >= 3:
                                    data["channel_auto_rebalance"][cp]["enabled"] = False
                                    _log_journal(
                                        f"⚠️ Auto-rebalance DISABLED: {alias}",
                                        f"3 consecutive failures — channel may be structurally bad. Re-enable manually from Channels page.",
                                        "warning"
                                    )
                                    print(f"[AUTO-REBAL] {alias} disabled after 3 consecutive failures")
                                else:
                                    _log_journal(
                                        f"Auto-rebalance failed: {alias}",
                                        f"Attempt {fails}/3 | Reason: {reason} | Route: {alias} → {dst_alias}",
                                        "auto-rebalance"
                                    )
                                with open(_DATA_JSON_PATH, "w") as f:
                                    json.dump(data, f, indent=2)
                    except Exception as e:
                        print(f"[AUTO-REBAL] {alias} failed: {e}")
                    
                    # Update last_run
                    data = json.load(open(_DATA_JSON_PATH))
                    if cp in data.get("channel_auto_rebalance", {}):
                        data["channel_auto_rebalance"][cp]["last_run"] = now
                        with open(_DATA_JSON_PATH, "w") as f:
                            json.dump(data, f, indent=2)
            
            # Also run global rebalance if configured
            hours = int(data.get("auto_rebalance_hours", 0))
            if hours > 0 and not MOCK:
                channels = run_lncli("listchannels")["channels"]
                overfull = [c for c in channels if int(c["capacity"]) > 0 and
                            int(c["local_balance"]) / int(c["capacity"]) > 0.80]
                underfull = [c for c in channels if int(c["capacity"]) > 0 and
                             int(c["local_balance"]) / int(c["capacity"]) < 0.20]
                if overfull and underfull:
                    rebalance_channels()
        except Exception as e:
            print(f"[AUTO-REBAL] Error: {e}")
        
        # Check every hour
        threading.Event().wait(3600)

def drain_trap_worker():
    while True:
        try:
            data = json.load(open(_DATA_JSON_PATH))
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
                        with open(_DATA_JSON_PATH, "w") as f:
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
                        with open(_DATA_JSON_PATH, "w") as f:
                            json.dump(data, f, indent=2)
        except Exception as e:
            pass
        threading.Event().wait(300)  # Check every 5 minutes

drain_trap_thread = threading.Thread(target=drain_trap_worker, daemon=True)
drain_trap_thread.start()


# ── Loop Out ──────────────────────────────────────────────────────────────────
def _find_loop_bin():
    """Where the `loop` program lives: LCC_LOOP_PATH, then PATH, then the usual places."""
    import shutil as _sh
    for c in (os.environ.get("LCC_LOOP_PATH", ""), _sh.which("loop") or "",
              os.path.expanduser("~/go/bin/loop"), "/usr/local/bin/loop"):
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


_LOOP_BIN = _find_loop_bin()
LOOP_NODE_PUBKEY = "021c97a90a411ff2b10dc2a8e32de2f29d2fa49d41bfbb52bd416e460db0747d0d"
LCC_ONCHAIN_RESERVE = int(os.environ.get("LCC_ONCHAIN_RESERVE", "1000000") or 0)


def run_loop(cmd, *args, input_text=None, timeout=90):
    """Run loop CLI command"""
    import subprocess
    if not _LOOP_BIN:
        return "loop is not installed on this node"
    result = subprocess.run([_LOOP_BIN, cmd] + list(args), capture_output=True, text=True,
                            input=input_text, timeout=timeout)
    return result.stdout + result.stderr


def _parse_loop_quote(output):
    """Read the numbers out of `loop quote in|out --verbose`."""
    labels = {
        "Send off-chain": "send_sats", "Receive on-chain": "receive_sats",
        "Send on-chain": "send_sats", "Receive off-chain": "receive_sats",
        "Estimated on-chain fee": "onchain_fee", "Loop service fee": "service_fee",
        "Estimated total fee": "total_fee", "No show penalty (prepay)": "prepay",
    }
    data = {}
    for line in output.splitlines():
        if ":" not in line:
            continue
        label, val = line.split(":", 1)
        key = labels.get(label.strip())
        if key:
            digits = "".join(c for c in val if c.isdigit())
            if digits:
                data[key] = int(digits)
    return data


def _loop_route_estimate(amt, scid):
    """Routing fee to reach the Loop node from one channel (the part Loop's quote leaves out)."""
    try:
        r = _lnd_rest("GET", f"/v1/graph/routes/{LOOP_NODE_PUBKEY}/{int(amt)}",
                      params={"outgoing_chan_id": scid, "use_mission_control": "true",
                              "fee_limit.fixed": max(5000, int(amt) // 50)}, timeout=15)
        routes = r.get("routes") or []
        if routes:
            return int(routes[0].get("total_fees", 0))
    except Exception:
        pass
    return None

@app.put("/api/journal/{entry_id}")
def update_journal_entry(entry_id: str, body: dict = Body(...)):
    try:
        journal_path = os.path.join(LCC_DATA_DIR, "journal.json")
        journal = json.load(open(journal_path)) if os.path.exists(journal_path) else []
        for entry in journal:
            if str(entry.get("id")) == str(entry_id):
                if "title" in body: entry["title"] = body["title"]
                if "body" in body: entry["body"] = body["body"]
                if "tag" in body: entry["tag"] = body["tag"]
                entry["edited"] = True
                json.dump(journal, open(journal_path, "w"))
                return {"success": True}
        return {"success": False, "error": "Entry not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/loop/monitor")
def loop_monitor():
    """Get recent loop swap history"""
    if not _LOOP_BIN:
        return {"swaps": [], "error": "Loop is not installed on this node"}
    import subprocess, json as _json
    result = subprocess.run(
        [_LOOP_BIN, 'listswaps'],
        capture_output=True, text=True, timeout=10
    )
    try:
        data = _json.loads(result.stdout)
        swaps = []
        for s in data.get("swaps", []):
            amt = int(s.get("amt", 0))
            state = s.get("state", "UNKNOWN")
            swap_type = s.get("type", "")
            cost_server = int(s.get("cost_server", 0))
            cost_onchain = int(s.get("cost_onchain", 0))
            cost_offchain = int(s.get("cost_offchain", 0))
            total_cost = cost_server + cost_onchain + cost_offchain
            swap_id = s.get("id", "")[:12]
            # Look up channel alias from saved mappings
            data = json.load(open(_DATA_JSON_PATH))
            chan_alias = data.get("loop_swaps", {}).get(swap_id, "")
            # Parse timestamp
            init_time = s.get("initiation_time", "0")
            try:
                import datetime
                ts = int(init_time) // 1000000000  # nanoseconds to seconds
                time_str = datetime.datetime.fromtimestamp(ts).strftime("%m/%d/%Y %I:%M %p")
            except:
                time_str = ""
            swaps.append({
                "id": swap_id,
                "type": swap_type,
                "amount": amt,
                "state": state,
                "cost_server": cost_server,
                "cost_onchain": cost_onchain,
                "cost_offchain": cost_offchain,
                "total_cost": total_cost,
                "channel": chan_alias,
                "quoted_fee": int(data.get("loop_quotes", {}).get(swap_id, 0) or 0),
                "time": time_str,
            })
        return {"swaps": swaps}
    except:
        return {"swaps": [], "error": result.stderr.strip()}

@app.get("/api/pendingchannels")
def get_pending_channels():
    data = run_lncli("pendingchannels")
    opening = []
    for c in data.get("pending_open_channels", []):
        ch = c.get("channel", {})
        opening.append({
            "remote_pub": ch.get("remote_node_pub", "")[:20],
            "capacity": int(ch.get("capacity", 0)),
            "local_balance": int(ch.get("local_balance", 0)),
            "confirmations_left": c.get("confirmations_until_active", 0),
            "initiator": ch.get("initiator", "") == "INITIATOR_LOCAL"
        })
    closing = []
    for c in data.get("waiting_close_channels", []) + data.get("pending_force_closing_channels", []):
        ch = c.get("channel", {})
        closing.append({
            "remote_pub": ch.get("remote_node_pub", "")[:20],
            "local_balance": int(ch.get("local_balance", 0)),
            "blocks_til_maturity": c.get("blocks_til_maturity", 0)
        })
    return {
        "pending_open": opening,
        "pending_closing": closing,
        "total_limbo": int(data.get("total_limbo_balance", 0))
    }

@app.get("/api/loop/quote")
def loop_quote(amt: int, scid: str = ""):
    if not _LOOP_BIN:
        return {"error": "Loop is not installed on this node"}
    try:
        output = run_loop('quote', 'out', str(int(amt)), '--verbose')
        data = _parse_loop_quote(output)
        if "total_fee" not in data:
            if "below min" in output.lower() or "amount must be" in output.lower():
                return {"error": "Amount is below the Loop Out minimum"}
            return {"error": "Could not read the Loop quote", "raw": output[-400:]}
        data["routing_estimate"] = _loop_route_estimate(amt, scid) if scid else None
        return data
    except Exception as e:
        return {"error": str(e)}

from pydantic import BaseModel as LoopBaseModel
class LoopOutRequest(LoopBaseModel):
    amt: int
    scid: str
    conf_target: int = 10
    max_routing_fee: int = 0
    quoted_fee: int = 0

@app.post("/api/loop/out")
def loop_out(req: LoopOutRequest):
    if not _LOOP_BIN:
        return {"success": False, "error": "Loop is not installed on this node"}
    try:
        # Look up channel alias before initiating
        chan_alias = req.scid
        try:
            channels = run_lncli("listchannels")["channels"]
            for c in channels:
                if c.get("scid") == req.scid or c.get("chan_id") == req.scid:
                    chan_alias = c.get("peer_alias", req.scid)
                    break
        except:
            pass
        output = run_loop('out',
            f'--amt={req.amt}',
            f'--conf_target={req.conf_target}',
            f'--channel={req.scid}',
            *([f'--max_swap_routing_fee={int(req.max_routing_fee)}'] if req.max_routing_fee and req.max_routing_fee > 0 else []),
            '--verbose',
            input_text='y\n')
        if 'Swap initiated' in output or 'ID:' in output:
            swap_id = ''
            for line in output.split('\n'):
                if line.strip().startswith('ID:'):
                    swap_id = line.split('ID:')[-1].strip()
            # Save swap-to-channel mapping
            data = json.load(open(_DATA_JSON_PATH))
            if "loop_swaps" not in data:
                data["loop_swaps"] = {}
            data["loop_swaps"][swap_id[:12]] = chan_alias
            if req.quoted_fee:
                data.setdefault("loop_quotes", {})[swap_id[:12]] = int(req.quoted_fee)
            json.dump(data, open(_DATA_JSON_PATH, "w"))
            # Auto-journal entry
            try:
                import datetime
                journal_path = os.path.join(LCC_DATA_DIR, "journal.json")
                journal = json.load(open(journal_path)) if os.path.exists(journal_path) else []
                block_info = run_lncli("getinfo")
                block_height = block_info.get("block_height", 0)
                journal.insert(0, {
                    "id": swap_id[:8],
                    "title": f"🔄 Loop Out — {chan_alias}",
                    "body": f"Loop Out initiated: {int(req.amt):,} sats via {chan_alias}. Swap ID: {swap_id[:16]}. Conf target: {req.conf_target} blocks.",
                    "tag": "milestone",
                    "block": block_height,
                    "date": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                })
                json.dump(journal, open(journal_path, "w"))
            except Exception as je:
                print(f"[LOOP] Journal write failed: {je}")
            return {"success": True, "swap_id": swap_id, "raw": output}
        else:
            return {"success": False, "error": output}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/loop/status")
def loop_status():
    return {"available": bool(_LOOP_BIN), "reserve": LCC_ONCHAIN_RESERVE}


def _valid_pubkey(pk):
    return bool(_re_ff.fullmatch(r"[0-9a-fA-F]{66}", pk or ""))


@app.get("/api/loop/quote-in")
def loop_quote_in(amt: int, last_hop: str = ""):
    if not _LOOP_BIN:
        return {"error": "Loop is not installed on this node"}
    if last_hop and not _valid_pubkey(last_hop):
        return {"error": "Invalid peer pubkey"}
    try:
        extra = ['--last_hop', last_hop] if last_hop else []
        output = run_loop('quote', 'in', str(int(amt)), *extra, '--verbose')
        data = _parse_loop_quote(output)
        if "total_fee" not in data:
            if "below min" in output.lower() or "amount must be" in output.lower():
                return {"error": "Amount is below the Loop In minimum"}
            return {"error": "Could not read the Loop quote", "raw": output[-400:]}
        try:
            data["onchain_confirmed"] = int(run_lncli("walletbalance").get("confirmed_balance", 0))
        except Exception:
            data["onchain_confirmed"] = None
        data["reserve"] = LCC_ONCHAIN_RESERVE
        return data
    except Exception as e:
        return {"error": str(e)}


class LoopInRequest(LoopBaseModel):
    amt: int
    last_hop: str = ""
    alias: str = ""
    conf_target: int = 0
    quoted_fee: int = 0


@app.post("/api/loop/in")
def loop_in(req: LoopInRequest):
    if not _LOOP_BIN:
        return {"success": False, "error": "Loop is not installed on this node"}
    if req.last_hop and not _valid_pubkey(req.last_hop):
        return {"success": False, "error": "Invalid peer pubkey"}
    try:
        try:
            confirmed = int(run_lncli("walletbalance").get("confirmed_balance", 0))
            left = confirmed - int(req.amt)
            if left < LCC_ONCHAIN_RESERVE:
                return {"success": False, "error": f"This would leave {left:,} sats on-chain, below your {LCC_ONCHAIN_RESERVE:,} sat reserve (LCC_ONCHAIN_RESERVE)."}
        except HTTPException:
            pass
        args = [f'--amt={int(req.amt)}']
        if req.last_hop:
            args.append(f'--last_hop={req.last_hop}')
        if req.conf_target and req.conf_target > 0:
            args.append(f'--conf_target={int(req.conf_target)}')
        output = run_loop('in', *args, input_text='y\n', timeout=120)
        if 'Swap initiated' in output or 'ID:' in output:
            swap_id = ''
            for line in output.split('\n'):
                if line.strip().startswith('ID:'):
                    swap_id = line.split('ID:')[-1].strip()
            alias = (req.alias or "Loop In")[:60]
            data = json.load(open(_DATA_JSON_PATH))
            data.setdefault("loop_swaps", {})[swap_id[:12]] = alias
            if req.quoted_fee:
                data.setdefault("loop_quotes", {})[swap_id[:12]] = int(req.quoted_fee)
            with open(_DATA_JSON_PATH, "w") as f:
                json.dump(data, f, indent=2)
            try:
                _log_journal(f"\U0001F504 Loop In \u2014 {alias}",
                             f"Loop In started: {int(req.amt):,} sats arriving via {alias}. "
                             f"Quoted fee: {int(req.quoted_fee):,} sats. Swap ID: {swap_id[:16]}.",
                             "milestone")
            except Exception as je:
                print(f"[LOOP] Journal write failed: {je}")
            return {"success": True, "swap_id": swap_id, "raw": output}
        return {"success": False, "error": output[-600:]}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/channel-auto-rebalance")
def set_channel_auto_rebalance(body: dict = Body(...)):
    """Set per-channel auto-rebalance settings"""
    chan_point = body.get("chan_point", "")
    enabled = body.get("enabled", False)
    amount = int(body.get("amount", 10000))
    hours = int(body.get("hours", 24))
    max_fee = int(body.get("max_fee", 400))
    target_pct = int(body.get("target_pct", 50))
    
    if not chan_point:
        raise HTTPException(status_code=400, detail="chan_point required")
    
    data = json.load(open(_DATA_JSON_PATH))
    if "channel_auto_rebalance" not in data:
        data["channel_auto_rebalance"] = {}
    
    # Get channel alias for display
    alias = chan_point[:16]
    try:
        channels = run_lncli("listchannels")["channels"]
        for c in channels:
            if c.get("channel_point") == chan_point:
                alias = c.get("peer_alias", chan_point[:16])
                break
    except:
        pass
    
    mode = body.get("mode", "interval")
    scheduled_hours = body.get("scheduled_hours", [])
    
    data["channel_auto_rebalance"][chan_point] = {
        "enabled": enabled,
        "amount": amount,
        "hours": hours,
        "max_fee": max_fee,
        "target_pct": target_pct,
        "mode": mode,
        "scheduled_hours": scheduled_hours,
        "alias": alias,
        "last_run": data.get("channel_auto_rebalance", {}).get(chan_point, {}).get("last_run", 0),
        "consecutive_fails": data.get("channel_auto_rebalance", {}).get(chan_point, {}).get("consecutive_fails", 0)
    }
    
    with open(_DATA_JSON_PATH, "w") as f:
        json.dump(data, f, indent=2)
    
    return {"status": "success", "channel": alias, "enabled": enabled, "amount": amount, "hours": hours}

@app.get("/api/channel-auto-rebalance")
def get_channel_auto_rebalance():
    """Get all per-channel auto-rebalance settings"""
    data = json.load(open(_DATA_JSON_PATH))
    return {"channels": data.get("channel_auto_rebalance", {})}


@app.post("/api/channel-auto-fee")
def set_channel_auto_fee(body: dict = Body(...)):
    """Set per-channel auto-fee-by-liquidity settings. Fee drifts between
    a min and max based on current local balance ratio - high local balance
    (channel not draining) -> fee toward min to attract routing; low local
    balance (already draining) -> fee toward max to slow it down.
    apply_to_peer + peer_pubkey: same settings on every channel with that peer,
    and the fee follows their combined balance (LND forwards over any of them)."""
    chan_point = body.get("chan_point", "")
    enabled = body.get("enabled", False)
    min_base = int(body.get("min_base", 0))
    max_base = int(body.get("max_base", 1000))
    min_ppm = int(body.get("min_ppm", 50))
    max_ppm = int(body.get("max_ppm", 500))
    hours = int(body.get("hours", 6))
    peer_pubkey = body.get("peer_pubkey", "") if body.get("apply_to_peer") else ""

    if not chan_point and not peer_pubkey:
        raise HTTPException(status_code=400, detail="chan_point required")

    data = json.load(open(_DATA_JSON_PATH))
    if "channel_auto_fee" not in data:
        data["channel_auto_fee"] = {}

    try:
        channels = run_lncli("listchannels")["channels"]
    except Exception:
        channels = []
    if peer_pubkey:
        targets = [(c.get("channel_point", ""), c.get("peer_alias", peer_pubkey[:16]))
                   for c in channels if c.get("remote_pubkey") == peer_pubkey]
        if not targets:
            raise HTTPException(status_code=404, detail="No channels with that peer")
    else:
        alias = chan_point[:16]
        for c in channels:
            if c.get("channel_point") == chan_point:
                alias = c.get("peer_alias", chan_point[:16])
                break
        targets = [(chan_point, alias)]

    for cp, alias in targets:
        prev = data.get("channel_auto_fee", {}).get(cp, {})
        data["channel_auto_fee"][cp] = {
            "enabled": enabled,
            "min_base": min_base,
            "max_base": max_base,
            "min_ppm": min_ppm,
            "max_ppm": max_ppm,
            "hours": hours,
            "alias": alias,
            "peer_group": bool(peer_pubkey),
            "last_run": 0 if peer_pubkey else prev.get("last_run", 0),
            "last_base": prev.get("last_base"),
            "last_ppm": prev.get("last_ppm"),
        }

    with open(_DATA_JSON_PATH, "w") as f:
        json.dump(data, f, indent=2)

    return {"status": "success", "channel": targets[0][1], "channels": len(targets), "enabled": enabled}


@app.get("/api/channel-auto-fee")
def get_channel_auto_fee():
    """Get all per-channel auto-fee-by-liquidity settings"""
    data = json.load(open(_DATA_JSON_PATH))
    return {"channels": data.get("channel_auto_fee", {})}


@app.get("/api/rebalance-roi")
def get_rebalance_roi(days: int = 0):
    """Get ROI per channel — rebalance cost vs routing income over time."""
    data = json.load(open(_DATA_JSON_PATH))
    roi_entries = data.get("rebalance_roi", [])
    
    now_ts = int(time.time())
    start_ts = now_ts - (days * 86400) if days > 0 else 0
    
    # Get rebalance costs per channel from roi entries
    rebal_costs = {}
    rebal_counts = {}
    for e in roi_entries:
        if e.get("time", 0) < start_ts:
            continue
        ch = e.get("channel", "?")
        rebal_costs[ch] = rebal_costs.get(ch, 0) + e.get("fee_paid", 0)
        rebal_counts[ch] = rebal_counts.get(ch, 0) + 1
    
    # Get routing income per channel from fwdinghistory
    try:
        history = run_lncli("fwdinghistory", f"--start_time={start_ts}", "--max_events=5000")
        events = history.get("forwarding_events", [])
        
        # Build chan_id -> alias map
        channels = run_lncli("listchannels").get("channels", [])
        chan_map = {}
        for ch in channels:
            cid = ch.get("chan_id", "")
            alias = ch.get("peer_alias") or ch.get("remote_pubkey", "")[:12]
            if cid:
                chan_map[str(cid)] = alias
        
        routing_income = {}
        routing_events = {}
        routing_volume = {}
        for e in events:
            fee = int(e.get("fee", 0))
            vol = int(e.get("amt_out", 0))
            alias_in = e.get("peer_alias_in", "")
            alias_out = e.get("peer_alias_out", "")
            if "unable to lookup" in alias_in: alias_in = "Closed channels"
            if "unable to lookup" in alias_out: alias_out = "Closed channels"
            if not alias_in and not alias_out:
                continue
            # Credit fee to inbound channel only (avoids double counting)
            if alias_in:
                routing_income[alias_in] = routing_income.get(alias_in, 0) + fee
                routing_events[alias_in] = routing_events.get(alias_in, 0) + 1
                routing_volume[alias_in] = routing_volume.get(alias_in, 0) + vol
    except:
        routing_income = {}
        routing_events = {}
        routing_volume = {}
    
    # Merge all channel names
    all_channels = set(list(rebal_costs.keys()) + list(routing_income.keys()))
    
    results = []
    total_cost = 0
    total_earned = 0
    for ch in all_channels:
        cost = rebal_costs.get(ch, 0)
        earned = routing_income.get(ch, 0)
        net = earned - cost
        total_cost += cost
        total_earned += earned
        results.append({
            "channel": ch,
            "rebalances": rebal_counts.get(ch, 0),
            "rebalance_cost": cost,
            "routing_earned": earned,
            "routing_events": routing_events.get(ch, 0),
            "routing_volume": routing_volume.get(ch, 0),
            "net": net
        })
    
    results.sort(key=lambda x: x["net"], reverse=True)
    
    return {
        "channels": results,
        "summary": {
            "total_channels": len(results),
            "total_rebalance_cost": total_cost,
            "total_routing_earned": total_earned,
            "net": total_earned - total_cost
        }
    }

scheduler_thread = threading.Thread(target=auto_rebalance_job, daemon=True)
scheduler_thread.start()

def auto_fee_job():
    """Background loop: nudge each enabled channel's fee between a min and
    max based on current local-liquidity ratio. High local balance (channel
    isn't draining) -> fee drifts toward min, to attract more routing.
    Low local balance (already draining) -> fee drifts toward max, to slow
    the drain and earn more per sat that does go out."""
    import time as _time
    while True:
        try:
            data = json.load(open(_DATA_JSON_PATH))
            per_channel = data.get("channel_auto_fee", {})
            now = int(_time.time())

            if per_channel and not MOCK:
                channels = run_lncli("listchannels")["channels"]
                chan_by_point = {c.get("channel_point", ""): c for c in channels}
                peer_tot = {}
                for _c in channels:
                    _t = peer_tot.setdefault(_c.get("remote_pubkey", ""), [0, 0, 0])
                    _t[0] += int(_c.get("local_balance", 0) or 0)
                    _t[1] += int(_c.get("capacity", 0) or 0)
                    _t[2] += 1
                fee_report = run_lncli("feereport").get("channel_fees", [])
                own_pubkey = run_lncli("getinfo").get("identity_pubkey", "")

                for cp, settings in list(per_channel.items()):
                    if not settings.get("enabled"):
                        continue

                    ch = chan_by_point.get(cp)
                    if not ch:
                        continue

                    interval = settings.get("hours", 6) * 3600
                    last_run = settings.get("last_run", 0)
                    if now - last_run < interval:
                        continue

                    cap = int(ch.get("capacity", 1))
                    local = int(ch.get("local_balance", 0))
                    ratio = (local / cap) if cap > 0 else 0.5  # 1.0 = fully local, 0.0 = fully drained
                    _pt = peer_tot.get(ch.get("remote_pubkey", ""), [0, 0, 0])
                    if settings.get("peer_group") and _pt[2] > 1 and _pt[1] > 0:
                        ratio = _pt[0] / _pt[1]  # all channels with this peer act as one pipe

                    min_base = int(settings.get("min_base", 0))
                    max_base = int(settings.get("max_base", 1000))
                    min_ppm = int(settings.get("min_ppm", 50))
                    max_ppm = int(settings.get("max_ppm", 500))
                    alias = settings.get("alias", cp[:16])

                    new_base = int(round(max_base - (max_base - min_base) * ratio))
                    new_ppm = int(round(max_ppm - (max_ppm - min_ppm) * ratio))
                    new_base = max(min_base, min(max_base, new_base))
                    new_ppm = max(min_ppm, min(max_ppm, new_ppm))

                    scid = str(ch.get("scid") or ch.get("chan_id", ""))
                    current_base, current_ppm = None, None
                    for fr in fee_report:
                        if str(fr.get("chan_id", "")) == scid:
                            current_base = int(fr.get("base_fee_msat", 0))
                            current_ppm = int(fr.get("fee_per_mil", 0))
                            break

                    if current_base == new_base and current_ppm == new_ppm:
                        data2 = json.load(open(_DATA_JSON_PATH))
                        if cp in data2.get("channel_auto_fee", {}):
                            data2["channel_auto_fee"][cp]["last_run"] = now
                            with open(_DATA_JSON_PATH, "w") as f:
                                json.dump(data2, f, indent=2)
                        continue

                    try:
                        chan_info = run_lncli("getchaninfo", f"--chan_point={cp}")
                        if chan_info.get("node1_pub") == own_pubkey:
                            tld = chan_info.get("node1_policy", {}).get("time_lock_delta", 40)
                        else:
                            tld = chan_info.get("node2_policy", {}).get("time_lock_delta", 40)

                        run_lncli(
                            "updatechanpolicy",
                            f"--base_fee_msat={new_base}",
                            f"--fee_rate_ppm={new_ppm}",
                            f"--time_lock_delta={tld}",
                            f"--chan_point={cp}",
                        )
                        print(f"[AUTO-FEE] {alias}: liquidity {ratio*100:.0f}% local -> base {new_base} msat / ppm {new_ppm}")
                        _log_journal(
                            f"Auto-fee adjusted: {alias}",
                            f"Liquidity {ratio*100:.0f}% local | Base: {current_base}\u2192{new_base} msat | PPM: {current_ppm}\u2192{new_ppm}",
                            "auto-fee"
                        )

                        data2 = json.load(open(_DATA_JSON_PATH))
                        if cp in data2.get("channel_auto_fee", {}):
                            data2["channel_auto_fee"][cp]["last_run"] = now
                            data2["channel_auto_fee"][cp]["last_base"] = new_base
                            data2["channel_auto_fee"][cp]["last_ppm"] = new_ppm
                            with open(_DATA_JSON_PATH, "w") as f:
                                json.dump(data2, f, indent=2)
                    except Exception as e:
                        print(f"[AUTO-FEE] {alias} failed: {e}")
        except Exception as e:
            print(f"[AUTO-FEE] job error: {e}")
        _time.sleep(3600)

fee_thread = threading.Thread(target=auto_fee_job, daemon=True)
fee_thread.start()

def roi_tracker_worker():
    """Check routing fees earned after each auto-rebalance — 2hr and 24hr windows"""
    import time as _t3
    while True:
        try:
            data = json.load(open(_DATA_JSON_PATH))
            roi_entries = data.get("rebalance_roi", [])
            now = int(_t3.time())
            updated = False
            
            for entry in roi_entries:
                rebal_time = entry.get("time", 0)
                chan_alias = entry.get("channel", "")
                
                # Skip if both windows already filled
                if entry.get("routing_2hr") is not None and entry.get("routing_24hr") is not None:
                    continue
                
                # Check 2hr window (after 2 hours have passed)
                if entry.get("routing_2hr") is None and now - rebal_time >= 7200:
                    try:
                        fwd = run_lncli("fwdinghistory", f"--start_time={rebal_time}", f"--end_time={rebal_time + 7200}", "--max_events=1000")
                        fees_2hr = sum(int(e.get("fee", 0)) for e in fwd.get("forwarding_events", [])
                                      if chan_alias.lower() in str(e.get("peer_alias_in", "")).lower() or
                                         chan_alias.lower() in str(e.get("peer_alias_out", "")).lower())
                        entry["routing_2hr"] = fees_2hr
                        updated = True
                        profit = fees_2hr - entry.get("fee_paid", 0)
                        _log_journal(
                            f"ROI 2hr: {chan_alias} {'✅' if profit >= 0 else '❌'} {'+' if profit >= 0 else ''}{profit} sats",
                            f"Rebalance fee: {entry.get('fee_paid', 0)} sats | Routing earned (2hr): {fees_2hr} sats | Net: {profit} sats",
                            "roi-tracker"
                        )
                    except:
                        pass
                
                # Check 24hr window (after 24 hours have passed)
                if entry.get("routing_24hr") is None and now - rebal_time >= 86400:
                    try:
                        fwd = run_lncli("fwdinghistory", f"--start_time={rebal_time}", f"--end_time={rebal_time + 86400}", "--max_events=1000")
                        fees_24hr = sum(int(e.get("fee", 0)) for e in fwd.get("forwarding_events", [])
                                       if chan_alias.lower() in str(e.get("peer_alias_in", "")).lower() or
                                          chan_alias.lower() in str(e.get("peer_alias_out", "")).lower())
                        entry["routing_24hr"] = fees_24hr
                        updated = True
                        profit = fees_24hr - entry.get("fee_paid", 0)
                        _log_journal(
                            f"ROI 24hr: {chan_alias} {'✅' if profit >= 0 else '❌'} {'+' if profit >= 0 else ''}{profit} sats",
                            f"Rebalance fee: {entry.get('fee_paid', 0)} sats | Routing earned (24hr): {fees_24hr} sats | Net: {profit} sats",
                            "roi-tracker"
                        )
                    except:
                        pass
            
            if updated:
                data["rebalance_roi"] = roi_entries
                with open(_DATA_JSON_PATH, "w") as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[ROI-TRACKER] Error: {e}")
        
        # Check every 30 minutes
        threading.Event().wait(1800)

roi_thread = threading.Thread(target=roi_tracker_worker, daemon=True)
roi_thread.start()


def _auto_reconnect_enabled():
    """Off unless the user turns it on. LND already retries channel peers
    by itself; this is an optional, faster nudge for routing nodes."""
    try:
        return bool(json.load(open(_DATA_JSON_PATH)).get("auto_reconnect_enabled", False))
    except Exception:
        return False


def auto_reconnect_worker():
    """Reconnect disconnected channel peers every 30 minutes, when enabled"""
    import time
    while True:
        try:
            threading.Event().wait(1800)  # Wait 30 minutes
            if not _auto_reconnect_enabled():
                continue
            channels = run_lncli("listchannels")
            peers = run_lncli("listpeers")
            connected_pubkeys = set(p.get("pub_key", "") for p in peers.get("peers", []))
            for ch in channels.get("channels", []):
                pubkey = ch.get("remote_pubkey", "")
                if pubkey and pubkey not in connected_pubkeys:
                    # Get peer address from node info
                    try:
                        node_info = run_lncli("getnodeinfo", f"--pub_key={pubkey}")
                        addresses = node_info.get("node", {}).get("addresses", [])
                        if addresses:
                            addr = f"{pubkey}@{addresses[0].get('addr', '')}"
                            run_lncli("connect", addr)
                            print(f"[RECONNECT] Reconnected to {ch.get('peer_alias', pubkey[:16])}")
                    except:
                        pass
        except Exception as e:
            print(f"[RECONNECT] Error: {e}")

reconnect_thread = threading.Thread(target=auto_reconnect_worker, daemon=True)
reconnect_thread.start()
