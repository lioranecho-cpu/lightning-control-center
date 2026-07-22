#!/bin/bash

# ⚡ Lightning Control Center — One-Command Installer
# Usage: curl -sSL https://raw.githubusercontent.com/lioranecho-cpu/lightning-control-center/main/install.sh | bash

set -e

# ── Colors ──────────────────────────────────────────────────────────────────
ORANGE='\033[0;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── Banner ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${ORANGE}${BOLD}"
echo "  ⚡ Lightning Control Center"
echo "  ─────────────────────────────"
echo "  v0.1.0 Community Edition"
echo "  Made with ⚡ and ₿ for the Bitcoin community"
echo -e "${NC}"
echo ""

# ── Check OS ─────────────────────────────────────────────────────────────────
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}❌ LCC installer requires Linux. For Mac/Windows, access LCC via browser.${NC}"
    exit 1
fi

echo -e "${BLUE}▶ Checking requirements...${NC}"

# ── Check Python ──────────────────────────────────────────────────────────────
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Install it with: sudo apt install python3 python3-pip${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# ── Check pip ────────────────────────────────────────────────────────────────
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ pip3 not found. Install it with: sudo apt install python3-pip${NC}"
    exit 1
fi
echo -e "${GREEN}✓ pip3 found${NC}"

# ── Check git ────────────────────────────────────────────────────────────────
if ! command -v git &> /dev/null; then
    echo -e "${ORANGE}▶ Installing git...${NC}"
    sudo apt-get install -y git
fi
echo -e "${GREEN}✓ git found${NC}"

echo ""

# ── Install location ─────────────────────────────────────────────────────────
DEFAULT_DIR="$HOME/lcc"
echo -e "${BLUE}▶ Where should LCC be installed?${NC}"
echo -e "  Press Enter for default: ${BOLD}$DEFAULT_DIR${NC}"
read -r -p "  Install directory: " INSTALL_DIR
INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_DIR}"

# ── Download LCC ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}▶ Downloading Lightning Control Center...${NC}"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${ORANGE}⚠ Directory $INSTALL_DIR already exists.${NC}"
    read -r -p "  Overwrite? (y/N): " OVERWRITE
    if [[ "$OVERWRITE" =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
    else
        echo "Installation cancelled."
        exit 0
    fi
fi

git clone https://github.com/lioranecho-cpu/lightning-control-center.git "$INSTALL_DIR"
echo -e "${GREEN}✓ LCC downloaded to $INSTALL_DIR${NC}"

# ── Install Python dependencies ───────────────────────────────────────────────
echo ""
echo -e "${BLUE}▶ Installing Python dependencies...${NC}"
pip3 install fastapi uvicorn aiofiles psutil --break-system-packages --quiet
echo -e "${GREEN}✓ Dependencies installed${NC}"

# ── Configure password ────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}▶ Set your LCC password${NC}"
echo -e "  This protects access to your node dashboard."
echo ""
while true; do
    read -r -s -p "  Enter password: " LCC_PASSWORD
    echo ""
    read -r -s -p "  Confirm password: " LCC_PASSWORD2
    echo ""
    if [ "$LCC_PASSWORD" = "$LCC_PASSWORD2" ]; then
        if [ ${#LCC_PASSWORD} -lt 6 ]; then
            echo -e "${RED}  ❌ Password must be at least 6 characters${NC}"
        else
            break
        fi
    else
        echo -e "${RED}  ❌ Passwords do not match, try again${NC}"
    fi
done

# Update password in login.html
sed -i "s|const LCC_PASSWORD_HASH = 'lcc2026'|const LCC_PASSWORD_HASH = '$LCC_PASSWORD'|g" "$INSTALL_DIR/login.html"
echo -e "${GREEN}✓ Password set${NC}"

# ── Configure Bitcoin Core RPC ────────────────────────────────────────────────
echo ""
echo -e "${BLUE}▶ Configure Bitcoin Core connection${NC}"
echo ""

# Auto-detect bitcoin.conf
BITCOIN_CONF=""
POSSIBLE_CONFS=(
    "$HOME/.bitcoin/bitcoin.conf"
    "$HOME/snap/bitcoin-core/common/.bitcoin/bitcoin.conf"
    "/etc/bitcoin/bitcoin.conf"
    "/mnt/bitcoin/home/$USER/snap/bitcoin-core/common/.bitcoin/bitcoin.conf"
)

for conf in "${POSSIBLE_CONFS[@]}"; do
    if [ -f "$conf" ]; then
        BITCOIN_CONF="$conf"
        echo -e "${GREEN}✓ Found bitcoin.conf at: $conf${NC}"
        RPC_USER=$(grep "^rpcuser=" "$conf" | cut -d'=' -f2)
        RPC_PASS=$(grep "^rpcpassword=" "$conf" | cut -d'=' -f2)
        break
    fi
done

if [ -z "$BITCOIN_CONF" ]; then
    echo -e "${ORANGE}⚠ Could not auto-detect bitcoin.conf${NC}"
    read -r -p "  RPC Username: " RPC_USER
    read -r -s -p "  RPC Password: " RPC_PASS
    echo ""
fi

if [ -n "$RPC_USER" ] && [ -n "$RPC_PASS" ]; then
    echo -e "${GREEN}✓ RPC credentials found: user=$RPC_USER${NC}"
fi

# Auto-detect bitcoin-cli path
BITCOIN_CLI=""
POSSIBLE_PATHS=(
    "/snap/bitcoin-core/current/bin/bitcoin-cli"
    "/usr/bin/bitcoin-cli"
    "/usr/local/bin/bitcoin-cli"
)

for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -f "$path" ]; then
        BITCOIN_CLI="$path"
        echo -e "${GREEN}✓ Found bitcoin-cli at: $path${NC}"
        break
    fi
done

if [ -z "$BITCOIN_CLI" ]; then
    BITCOIN_CLI=$(which bitcoin-cli 2>/dev/null || echo "")
    if [ -n "$BITCOIN_CLI" ]; then
        echo -e "${GREEN}✓ Found bitcoin-cli at: $BITCOIN_CLI${NC}"
    else
        echo -e "${ORANGE}⚠ bitcoin-cli not found — you can set it manually in lcc_api.py${NC}"
        BITCOIN_CLI="/usr/bin/bitcoin-cli"
    fi
fi

# Update lcc_api.py with credentials
if [ -n "$RPC_USER" ] && [ -n "$RPC_PASS" ]; then
    sed -i "s|bitcoin-cli\"] + list(args)|$BITCOIN_CLI\", \"-rpcuser=$RPC_USER\", \"-rpcpassword=$RPC_PASS\"] + list(args)|g" "$INSTALL_DIR/lcc_api.py"
    echo -e "${GREEN}✓ lcc_api.py configured${NC}"
fi

# ── Set up systemd service ─────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}▶ Set up automatic startup?${NC}"
read -r -p "  Run LCC as a system service (starts on boot)? (Y/n): " SETUP_SERVICE
SETUP_SERVICE="${SETUP_SERVICE:-Y}"

UVICORN_PATH=$(which uvicorn 2>/dev/null || echo "$HOME/.local/bin/uvicorn")

if [[ "$SETUP_SERVICE" =~ ^[Yy]$ ]]; then
    sudo bash -c "cat > /etc/systemd/system/lcc.service << EOF
[Unit]
Description=Lightning Control Center
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$UVICORN_PATH lcc_api:app --host 0.0.0.0 --port 8765
Restart=always
RestartSec=5
Environment=PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF"

    sudo systemctl daemon-reload
    sudo systemctl enable lcc
    sudo systemctl start lcc
    sleep 2

    if systemctl is-active --quiet lcc; then
        echo -e "${GREEN}✓ LCC service started and enabled on boot${NC}"
    else
        echo -e "${ORANGE}⚠ Service may need manual start: sudo systemctl start lcc${NC}"
    fi
else
    echo -e "${ORANGE}  To start LCC manually: cd $INSTALL_DIR && uvicorn lcc_api:app --host 0.0.0.0 --port 8765${NC}"
fi

# ── Get local IP ──────────────────────────────────────────────────────────────
LOCAL_IP=$(hostname -I | awk '{print $1}')

# ── Done! ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}"
echo "  ✅ Lightning Control Center installed successfully!"
echo -e "${NC}"
echo -e "${ORANGE}${BOLD}  Access LCC:${NC}"
echo -e "  🖥️  This machine:  ${BOLD}http://localhost:8765/dashboard${NC}"
echo -e "  📱  Local network: ${BOLD}http://$LOCAL_IP:8765/dashboard${NC}"
echo ""
echo -e "${BLUE}  Default pages:${NC}"
echo -e "  Dashboard → http://localhost:8765/dashboard"
echo -e "  Login     → http://localhost:8765/static/login.html"
echo ""
echo -e "${ORANGE}  ⚠️  Remember:${NC}"
echo -e "  • Use the password you just set to log in"
echo -e "  • Sessions expire after 4 hours"
echo -e "  • Config file: $INSTALL_DIR/lcc_api.py"
echo ""
echo -e "${GREEN}  Made with ⚡ and ₿ by SatsList${NC}"
echo -e "  https://satslist.shop"
echo ""
