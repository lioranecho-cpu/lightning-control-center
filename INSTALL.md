# ⚡ Lightning Control Center — Installation Guide

Whether you're a seasoned node operator or just getting started, this guide will get LCC running on your hardware.

---

## 📋 What You Need Before Starting

| Requirement | Why |
|-------------|-----|
| A computer running Linux or macOS | LCC runs on your own hardware |
| Python 3.10 or newer | Runs the backend |
| A running Bitcoin Lightning node (LND) | LCC connects to your node |
| Bitcoin Core synced | For mempool and fee data |
| A web browser | Chrome, Firefox, Safari all work |

> **Don't have a node yet?** Check out [Umbrel](https://umbrel.com), [Start9](https://start9.com) or [RaspiBlitz](https://raspiblitz.org) for easy node setups. LCC works with all of them.

---

## ⚡ Quick Start (For Experienced Node Operators)

```bash
git clone https://github.com/lioranecho-cpu/lightning-control-center.git
cd lightning-control-center
pip3 install fastapi uvicorn aiofiles psutil --break-system-packages
```

Edit `lcc_api.py` — set your bitcoin-cli path and RPC credentials.
Edit `login.html` — set your password.

```bash
uvicorn lcc_api:app --host 0.0.0.0 --port 8765
```

Open `http://localhost:8765/dashboard` — done.

---

## 🐣 Step-by-Step Guide (For Everyone)

### Step 1 — Download LCC

**Option A — Download ZIP (easiest):**
1. Go to [github.com/lioranecho-cpu/lightning-control-center](https://github.com/lioranecho-cpu/lightning-control-center)
2. Click the green **Code** button
3. Click **Download ZIP**
4. Unzip the file somewhere easy to find (e.g. your home folder)

**Option B — Use Git:**
```bash
git clone https://github.com/lioranecho-cpu/lightning-control-center.git
```

---

### Step 2 — Install Python Dependencies

Open a terminal and navigate to your LCC folder:

```bash
cd lightning-control-center
```

Install the required packages:

```bash
pip3 install fastapi uvicorn aiofiles psutil --break-system-packages
```

You should see packages downloading and installing. This only needs to be done once.

---

### Step 3 — Configure Your Node Connection

Open `lcc_api.py` in a text editor (Notepad, TextEdit, nano — anything works).

Find these lines near the top and update them for your setup:

**If Bitcoin Core is installed via snap (Ubuntu):**
```python
# Find this line:
["/snap/bitcoin-core/current/bin/bitcoin-cli"] + list(args)

# And this section — add your RPC credentials:
["/snap/bitcoin-core/current/bin/bitcoin-cli", "-rpcuser=YOUR_USER", "-rpcpassword=YOUR_PASSWORD"] + list(args)
```

**Where to find your RPC credentials:**
- Look in your `bitcoin.conf` file
- Usually at `~/.bitcoin/bitcoin.conf` or `~/snap/bitcoin-core/common/.bitcoin/bitcoin.conf`
- Find the lines: `rpcuser=` and `rpcpassword=`

**If you're just testing (no real node):**
```bash
# Run in mock mode — uses sample data, no node needed
LCC_MOCK=true uvicorn lcc_api:app --host 0.0.0.0 --port 8765
```

---

### Step 4 — Set Your Password

Open `login.html` in a text editor.

Find this line:
```javascript
const LCC_PASSWORD_HASH = 'lcc2026';
```

Replace `lcc2026` with your own secure password:
```javascript
const LCC_PASSWORD_HASH = 'your-secure-password-here';
```

Save the file. **Do not share this password** — it protects access to your node data.

---

### Step 5 — Start LCC

In your terminal, from the `lightning-control-center` folder:

```bash
uvicorn lcc_api:app --host 0.0.0.0 --port 8765
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8765
INFO:     Application startup complete.
```

---

### Step 6 — Open LCC in Your Browser

Open your browser and go to:

```
http://localhost:8765/dashboard
```

Enter your password at the login screen → you're in! 🎉

---

## 🔁 Run LCC Automatically (Recommended)

To have LCC start automatically when your computer boots, set it up as a system service.

**On Linux (Ubuntu/Debian):**

Create the service file:
```bash
sudo nano /etc/systemd/system/lcc.service
```

Paste this (replace `YOUR_USERNAME` and `/path/to/lcc`):
```ini
[Unit]
Description=Lightning Control Center
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/lightning-control-center
ExecStart=/home/YOUR_USERNAME/.local/bin/uvicorn lcc_api:app --host 0.0.0.0 --port 8765
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable lcc
sudo systemctl start lcc
```

LCC now starts automatically on every boot.

---

## 🌐 Access LCC From Anywhere (Optional)

By default LCC is only accessible on your local network. To access it remotely:

**Option A — Cloudflare Tunnel (recommended, free):**
1. Install [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
2. Add to your tunnel config:
```yaml
ingress:
  - hostname: lcc.yourdomain.com
    service: http://localhost:8765
```
3. Access at `https://lcc.yourdomain.com`

**Option B — Local network only:**
Find your computer's local IP:
```bash
hostname -I
```
Access from other devices on your network at `http://YOUR_IP:8765/dashboard`

---

## 🔧 Troubleshooting

**"lncli not found" error:**
- Make sure LND is running: `systemctl status lnd` or `systemctl status litd`
- Check lncli is in your PATH: `which lncli`

**"bitcoin-cli not found" error:**
- Update the path in `lcc_api.py` to match your Bitcoin Core installation
- Snap install: `/snap/bitcoin-core/current/bin/bitcoin-cli`
- Standard install: `/usr/bin/bitcoin-cli`

**"Connection refused" on port 8765:**
- Make sure uvicorn is running
- Check with: `curl http://localhost:8765/`

**Wrong password at login:**
- Hard refresh your browser: `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)
- Browser may be caching an old version

**Page shows dashes instead of data:**
- Your node may not be fully synced yet
- Check Bitcoin Core: `bitcoin-cli getblockchaininfo`
- Check LND: `lncli getinfo`

---

## 📱 Mobile Access

LCC is fully mobile responsive. Once running, open `http://YOUR_IP:8765/dashboard` on your phone's browser while on the same WiFi network.

For remote mobile access, set up Cloudflare Tunnel (see above).

---

## 🔒 Security Notes

- LCC is protected by password login
- Sessions expire after 4 hours by default
- Never expose port 8765 directly to the internet without authentication
- Use Cloudflare Tunnel or a reverse proxy (Caddy/Nginx) for remote access
- Change the default password before deploying

---

## ❓ Getting Help

- **GitHub Issues:** [github.com/lioranecho-cpu/lightning-control-center/issues](https://github.com/lioranecho-cpu/lightning-control-center/issues)
- **SatsList:** [satslist.shop](https://satslist.shop)
- **Community:** Join the conversation on Bitcoin Twitter / Nostr

---

## ⚡ Upgrade to Pro

The Community Edition is free and open source.

For **Personal** and **Pro** editions with advanced features, visit [SatsList](https://satslist.shop) — pay in sats, no fiat required.

---

*Made with ⚡ and ₿ for the Bitcoin community.*
