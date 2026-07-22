# Add this to lcc_api.py before the app.mount line

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
