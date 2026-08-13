#!/usr/bin/env python3
"""
LCC NWC Relay Listener
Listens on wss://relay.damus.io for NWC requests addressed to this node,
decrypts them, calls lncli, and sends back encrypted responses.
"""
import asyncio
import json
import os
import subprocess
import time
import logging
from datetime import timedelta
from nostr_sdk import (
    Keys, SecretKey, PublicKey, Client, Filter,
    EventBuilder, nip04_decrypt, nip04_encrypt, nip44_encrypt, nip44_decrypt,
    Kind, RelayUrl, NostrSigner, Tag
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [NWC] %(message)s')
log = logging.getLogger(__name__)

RELAY = "wss://relay.primal.net"
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(DATA_DIR, "data.json")
NWC_CONNS = os.path.join(DATA_DIR, "nwc_connections.json")

def run_lncli(*args):
    try:
        result = subprocess.run(
            ["lncli"] + list(args),
            capture_output=True, text=True, timeout=30
        )
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except Exception as e:
        log.error(f"lncli error: {e}")
        return {}

def load_node_keys():
    with open(DATA_JSON) as f:
        d = json.load(f)
    nsec = d.get("nwc_nsec", "")
    if not nsec:
        raise Exception("No nwc_nsec in data.json")
    sk = SecretKey.parse(nsec)
    return Keys(sk)

def load_connections():
    if not os.path.exists(NWC_CONNS):
        return []
    with open(NWC_CONNS) as f:
        return json.load(f).get("connections", [])

def get_connection_by_pubkey(client_pubkey_hex):
    for c in load_connections():
        if not c.get("active"):
            continue
        try:
            pk = PublicKey.parse(c["client_pubkey"])
            if pk.to_hex() == client_pubkey_hex:
                return c
        except:
            continue
    return None

def update_last_used(conn_id):
    if not os.path.exists(NWC_CONNS):
        return
    with open(NWC_CONNS) as f:
        data = json.load(f)
    for c in data.get("connections", []):
        if c["id"] == conn_id:
            c["last_used"] = int(time.time())
    with open(NWC_CONNS, "w") as f:
        json.dump(data, f, indent=2)

def handle_get_balance():
    channel = run_lncli("channelbalance")
    balance = int(channel.get("local_balance", {}).get("sat", 0))
    return {"balance": balance * 1000}

def handle_pay_invoice(params, conn):
    invoice = params.get("invoice", "")
    if not invoice:
        return None, "INVALID_INVOICE"
    result = run_lncli("payinvoice", "--pay_req=" + invoice, "--force")
    if result.get("payment_error"):
        return None, result["payment_error"]
    return {
        "preimage": result.get("payment_preimage", ""),
        "fees_paid": int(result.get("fee", 0)) * 1000
    }, None

def handle_make_invoice(params):
    amount_msat = params.get("amount", 0)
    amount_sat = max(1, amount_msat // 1000)
    description = params.get("description", "LCC Invoice")
    expiry = params.get("expiry", 3600)
    result = run_lncli(
        "addinvoice",
        f"--amt={amount_sat}",
        f"--memo={description}",
        f"--expiry={expiry}"
    )
    if not result.get("payment_request"):
        return None, "INTERNAL"
    return {
        "type": "incoming",
        "invoice": result["payment_request"],
        "payment_hash": result.get("r_hash", ""),
        "amount": amount_msat,
        "description": description,
        "expires_at": int(time.time()) + expiry,
        "created_at": int(time.time())
    }, None

def handle_lookup_invoice(params):
    payment_hash = params.get("payment_hash", "")
    if not payment_hash:
        return None, "INVALID"
    result = run_lncli("lookupinvoice", payment_hash)
    if not result:
        return None, "NOT_FOUND"
    settled = result.get("settled", False)
    return {
        "type": "incoming",
        "invoice": result.get("payment_request", ""),
        "payment_hash": payment_hash,
        "amount": int(result.get("value", 0)) * 1000,
        "description": result.get("memo", ""),
        "preimage": result.get("r_preimage", "") if settled else None,
        "settled_at": int(result.get("settle_date", 0)) if settled else None,
        "created_at": int(result.get("creation_date", 0))
    }, None

def process_request(method, params, conn):
    perms = conn.get("permissions", [])
    if method == "get_info":
        # Get real block info from lncli
        try:
            info = json.loads(subprocess.run(["lncli", "getinfo"], capture_output=True, text=True, timeout=10).stdout)
            block_height = info.get("block_height", 0)
            block_hash = info.get("block_hash", "")
        except:
            block_height = 0
            block_hash = ""
        return {
            "alias": "prodeskltn-node",
            "color": "#f7931a",
            "pubkey": "03ee97ebe8b3e50c6272c3b33c7d730ad6722016ecb2d5fbfe9b0b7595383307d1",
            "network": "mainnet",
            "block_height": block_height,
            "block_hash": block_hash,
            "methods": ["get_balance", "get_info", "pay_invoice", "make_invoice", "lookup_invoice", "list_transactions"]
        }, None

    elif method == "get_balance":
        if "get_balance" not in perms:
            return None, "RESTRICTED"
        return handle_get_balance(), None
    elif method == "pay_invoice":
        if "pay_invoice" not in perms:
            return None, "RESTRICTED"
        return handle_pay_invoice(params, conn)
    elif method == "make_invoice":
        if "make_invoice" not in perms:
            return None, "RESTRICTED"
        return handle_make_invoice(params)
    elif method == "lookup_invoice":
        if "lookup_invoice" not in perms:
            return None, "RESTRICTED"
        return handle_lookup_invoice(params)
    elif method == "list_transactions":
        if "list_transactions" not in perms:
            return None, "RESTRICTED"
        txs = run_lncli("listpayments", "--max_payments=20", "--reversed")
        invoices = run_lncli("listinvoices", "--num_max_invoices=20", "--reversed")
        result = []
        for p in txs.get("payments", []):
            if p.get("status") == "SUCCEEDED":
                result.append({
                    "type": "outgoing",
                    "invoice": p.get("payment_request", ""),
                    "payment_hash": p.get("payment_hash", ""),
                    "amount": int(p.get("value_msat", 0)),
                    "fees_paid": int(p.get("fee_msat", 0)),
                    "description": p.get("description", ""),
                    "created_at": int(p.get("creation_time_ns", 0)) // 1_000_000_000,
                    "settled_at": int(p.get("creation_time_ns", 0)) // 1_000_000_000,
                })
        for inv in invoices.get("invoices", []):
            if inv.get("settled"):
                result.append({
                    "type": "incoming",
                    "invoice": inv.get("payment_request", ""),
                    "payment_hash": inv.get("r_hash", ""),
                    "amount": int(inv.get("amt_paid_msat", 0)),
                    "fees_paid": 0,
                    "description": inv.get("memo", ""),
                    "created_at": int(inv.get("creation_date", 0)),
                    "settled_at": int(inv.get("settle_date", 0)),
                })
        # Sort by settled_at descending
        result.sort(key=lambda x: x.get("settled_at", 0), reverse=True)
        return {"transactions": result[:20]}, None

    else:
        return None, "NOT_IMPLEMENTED"

async def run_listener():
    log.info("Starting NWC listener...")
    keys = load_node_keys()
    node_pubkey = keys.public_key()
    log.info(f"Node pubkey: {node_pubkey.to_bech32()}")

    while True:
        try:
            signer = NostrSigner.keys(keys)
            client = Client(signer)
            await client.add_relay(RelayUrl.parse(RELAY))
            await client.connect()
            log.info(f"✅ Connected to {RELAY}")

            # Publish NIP-47 info event (kind 13194) — tells wallets we exist
            capabilities = "get_info get_balance make_invoice lookup_invoice list_transactions pay_invoice"
            info_builder = EventBuilder(Kind(13194), capabilities)
            await client.send_event_builder(info_builder)
            log.info(f"📢 Published NWC info event (kind 13194) with capabilities: {capabilities}")

            # Subscribe to NWC request events (kind 23194) addressed to us
            from nostr_sdk import Timestamp
            f = Filter().kind(Kind(23194)).pubkeys([node_pubkey]).since(Timestamp.now())

            seen_events = set()
            log.info("👂 Listening for NWC requests...")
            while True:
                try:
                    stream = await client.stream_events(f, timedelta(hours=1))
                    while True:
                        event = await stream.next()
                        if event is None:
                            # Timeout — resubscribe
                            break

                        # Skip already-processed events
                        event_id = event.id().to_hex()
                        if event_id in seen_events:
                            continue
                        seen_events.add(event_id)
                        if len(seen_events) > 1000:
                            seen_events.clear()

                        sender_pubkey = event.author()
                        conn = get_connection_by_pubkey(sender_pubkey.to_hex())
                        if not conn:
                            log.warning(f"Unknown pubkey: {sender_pubkey.to_hex()[:16]}...")
                            continue

                        # Decrypt request
                        # Try NIP-44 first, fall back to NIP-04 — track which was used
                        used_nip44 = False
                        try:
                            content = nip44_decrypt(keys.secret_key(), sender_pubkey, event.content())
                            used_nip44 = True
                        except:
                            content = nip04_decrypt(keys.secret_key(), sender_pubkey, event.content())
                            used_nip44 = False
                        req = json.loads(content)
                        method = req.get("method", "")
                        params = req.get("params", {})
                        req_id = req.get("id", "")
                        log.info(f"⚡ NWC request: {method} from {conn['name']}")

                        # Process
                        result, error_code = process_request(method, params, conn)
                        update_last_used(conn["id"])

                        # Build response
                        if error_code:
                            response = {
                                "result_type": method,
                                "error": {"code": error_code, "message": error_code}
                            }
                        else:
                            response = {
                                "result_type": method,
                                "result": result
                            }
                        # Add id if present in request
                        if req_id:
                            response["id"] = req_id

                        # Encrypt response using same method client used
                        if used_nip44:
                            from nostr_sdk import Nip44Version
                            encrypted = nip44_encrypt(keys.secret_key(), sender_pubkey, json.dumps(response), Nip44Version.V2)
                        else:
                            encrypted = nip04_encrypt(keys.secret_key(), sender_pubkey, json.dumps(response))
                        resp_event = EventBuilder(Kind(23195), encrypted) \
                            .tags([
                                Tag.parse(["p", sender_pubkey.to_hex()]),
                                Tag.parse(["e", event.id().to_hex()])
                            ])
                        await client.send_event_builder(resp_event)
                        log.info(f"✅ Response sent for {method}")

                except Exception as e:
                    log.error(f"Stream error: {e}")
                    await asyncio.sleep(5)
                    break

        except Exception as e:
            log.error(f"Connection error: {e} — retrying in 30s")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(run_listener())
