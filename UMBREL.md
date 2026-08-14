# ⚡ Lightning Control Center — Umbrel Guide

## Install Options

### 🧪 Beta (Available Now) — Manual Sideload via SSH

For technical users who want early access before App Store approval.

**Requirements:**
- Umbrel with Bitcoin and Lightning apps installed and synced
- SSH access to your Umbrel device

**Steps:**

1. SSH into your Umbrel:
```bash
ssh umbrel@umbrel.local
```

2. Navigate to the apps directory:
```bash
cd ~/umbrel/app-data
```

3. Create the LCC folder:
```bash
mkdir lightning-control-center && cd lightning-control-center
```

4. Download the app files:
```bash
curl -O https://raw.githubusercontent.com/lioranecho-cpu/umbrel-apps/master/lightning-control-center/umbrel-app.yml
curl -O https://raw.githubusercontent.com/lioranecho-cpu/umbrel-apps/master/lightning-control-center/docker-compose.yml
```

5. Install:
```bash
~/umbrel/scripts/app install lightning-control-center
```

6. Access LCC at `http://umbrel.local:8766`

---

### 🛍️ App Store (Coming Soon)

Pending approval — PR #5983 at github.com/getumbrel/umbrel-apps

Once approved — one click install from your Umbrel dashboard.

---

## Need Help?
- GitHub: github.com/lioranecho-cpu/lightning-control-center
- Manual: github.com/lioranecho-cpu/lightning-control-center/blob/main/MANUAL.md
- Issues: github.com/lioranecho-cpu/lightning-control-center/issues

---

## 🤖 AI-Assisted Installation

Not sure where to start? Paste this prompt into [Claude](https://claude.ai) for step-by-step guided installation:

> I want to sideload Lightning Control Center (LCC) on my Umbrel node. LCC is a browser-based Lightning node management dashboard by Sparkie Labs. GitHub: https://github.com/lioranecho-cpu/lightning-control-center — Please guide me through the manual sideload installation on my Umbrel device step by step. Ask me what I need along the way.

Claude will ask for your Umbrel details and walk you through every step.
