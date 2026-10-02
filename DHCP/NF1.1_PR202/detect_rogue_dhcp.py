#!/usr/bin/env python3
"""Detector de servidors DHCP no autoritzats basat en tcpdump."""
import re
import subprocess
from prometheus_client import start_http_server, Gauge

LEGITIMATE_SERVER = "172.24.63.10"
INTERFACE = "enp0s3"
LOG_FILE = "/var/log/dhcp-rogue.log"

rogue_metric = Gauge(
    "dhcp_rogue_server_detected",
    "Servidor DHCP no autoritzat detectat (1=si, 0=no)"
)

def log_alert(server_ip):
    with open(LOG_FILE, "a") as f:
        f.write(f"[ALERT] Rogue DHCP detected from {server_ip}\n")
    print(f"[ALERT] Rogue DHCP detected from {server_ip}")

def monitor():
    proc = subprocess.Popen(
        ["tcpdump", "-i", INTERFACE, "-l", "-n", "port", "67", "or", "port", "68"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    )
    for line in proc.stdout:
        if "BOOTP/DHCP, Reply" in line or "DHCP-Message Option 53, length 1: Offer" in line:
            ips = re.findall(r"\d+\.\d+\.\d+\.\d+", line)
            if ips and ips[0] != LEGITIMATE_SERVER:
                rogue_metric.set(1)
                log_alert(ips[0])

if __name__ == "__main__":
    start_http_server(9101)
    monitor()